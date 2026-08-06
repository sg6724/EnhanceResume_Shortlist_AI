from __future__ import annotations

import asyncio
import json
import re

from ..config import settings
from ..services.llm import generate
from ..services.scoring import compute_bm25_score, compute_semantic_score

_MODEL = "gemini-2.5-flash"
_GROQ_MODEL = "llama-3.3-70b-versatile"


def _covered(term: str, resume_lower: str) -> bool:
    normalized = re.sub(r"[^a-z0-9+#.]+", " ", term.lower()).strip()
    if not normalized:
        return False
    if normalized in resume_lower:
        return True
    tokens = [t for t in normalized.split() if len(t) > 2]
    return bool(tokens) and all(t in resume_lower for t in tokens)


def _coverage(terms: list[str], resume_lower: str) -> tuple[float, list[str], list[str]]:
    if not terms:
        return 0.5, [], []
    matched = [term for term in terms if _covered(term, resume_lower)]
    missing = [term for term in terms if term not in matched]
    return len(matched) / len(terms), matched, missing


async def compute_match(
    jd_text: str,
    resume_plain_text: str,
    position_context: str,
    skill_terms: list[str] | None = None,
    must_have_skills: list[str] | None = None,
    nice_to_have_skills: list[str] | None = None,
    tech_stack: list[str] | None = None,
    seniority: str | None = None,
    location: str | None = None,
) -> dict:
    """
    ATS-style score with the existing DB-compatible output fields.
    composite_score is deterministic and capped when must-have coverage is low.
    """
    must = must_have_skills or []
    nice = nice_to_have_skills or []
    tech = tech_stack or []
    structured_terms = must + nice + tech
    keyword_query = " ".join(skill_terms or structured_terms) if (skill_terms or structured_terms) else jd_text

    kw_score = compute_bm25_score(keyword_query, resume_plain_text)
    sem_score = await asyncio.to_thread(compute_semantic_score, jd_text, resume_plain_text)

    resume_lower = resume_plain_text.lower()
    must_score, matched_must, missing_must = _coverage(must, resume_lower)
    nice_score, matched_nice, missing_nice = _coverage(nice, resume_lower)
    tech_score, matched_tech, missing_tech = _coverage(tech, resume_lower)

    seniority_score = 1.0
    if seniority and seniority.lower() in {"senior", "staff", "principal", "lead"}:
        seniority_score = 1.0 if seniority.lower() in resume_lower else 0.75

    location_score = 1.0
    if location and "remote" not in location.lower() and "remote" in resume_lower:
        location_score = 0.9

    deterministic_score = (
        0.45 * (must_score if must else kw_score)
        + 0.15 * nice_score
        + 0.15 * tech_score
        + 0.15 * sem_score
        + 0.05 * seniority_score
        + 0.05 * location_score
    )
    if must and must_score < 0.5:
        deterministic_score = min(deterministic_score, 0.58)
    elif must and must_score < 0.7:
        deterministic_score = min(deterministic_score, 0.72)

    matched_skills = matched_must + matched_nice + matched_tech
    missing_skills = missing_must + missing_nice + missing_tech
    gap_analysis = (
        f"Must-have coverage: {len(matched_must)}/{len(must) if must else 0}\n"
        f"Nice-to-have coverage: {len(matched_nice)}/{len(nice) if nice else 0}\n"
        f"Tech coverage: {len(matched_tech)}/{len(tech) if tech else 0}\n"
        f"Missing must-haves: {', '.join(missing_must) if missing_must else 'none'}"
    )

    if settings.gemini_api_key or settings.groq_api_key:
        prompt = f"""You are evaluating resume-to-JD fit.
Target position: {position_context}

JD (truncated to 2000 chars):
{jd_text[:2000]}

Resume plain text (truncated to 2000 chars):
{resume_plain_text[:2000]}

Deterministic ATS findings:
{gap_analysis}

Respond in valid JSON only, no markdown fences:
{{
  "gap_analysis": "short, specific gap analysis",
  "matched_skills": ["skill present in resume that satisfies the JD"],
  "missing_skills": ["JD requirement absent or weak in resume"]
}}"""
        try:
            raw = await generate(prompt, gemini_model=_MODEL, groq_model=_GROQ_MODEL)
            data = json.loads(raw.strip().strip("```json").strip("```").strip())
            gap_analysis = data.get("gap_analysis") or gap_analysis
            matched_skills = matched_skills or [str(x) for x in (data.get("matched_skills") or []) if x]
            missing_skills = missing_skills or [str(x) for x in (data.get("missing_skills") or []) if x]
        except Exception as e:
            print(f"[matcher] LLM error: {e}")
            gap_analysis = f"{gap_analysis}\nLLM explanation failed: {e}"

    composite = round(max(0.0, min(1.0, deterministic_score)), 4)
    return {
        "keyword_score": round(kw_score, 4),
        "semantic_score": round(sem_score, 4),
        "llm_score": composite,
        "composite_score": composite,
        "gap_analysis": gap_analysis,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
    }
