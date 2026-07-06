from __future__ import annotations

import json

from google import genai

from ..config import settings
from ..services.scoring import compute_bm25_score, compute_semantic_score

_MODEL = "gemini-2.0-flash"


def _client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


async def compute_match(
    jd_text: str,
    resume_plain_text: str,
    position_context: str,
) -> dict:
    """
    Composite match score: BM25 30% + semantic embeddings 30% + LLM analysis 40%.
    Returns {keyword_score, semantic_score, llm_score, composite_score, gap_analysis}.
    """
    kw_score = compute_bm25_score(jd_text, resume_plain_text)
    sem_score = compute_semantic_score(jd_text, resume_plain_text)

    llm_score = 0.5
    gap_analysis = "LLM analysis skipped — no GEMINI_API_KEY"

    if settings.gemini_api_key:
        prompt = f"""You are evaluating resume-to-JD fit.
Target position: {position_context}

JD (truncated to 2000 chars):
{jd_text[:2000]}

Resume plain text (truncated to 2000 chars):
{resume_plain_text[:2000]}

Respond in valid JSON only, no markdown fences:
{{
  "score": 0.0_to_1.0,
  "gap_analysis": "• Missing skill 1\\n• Missing skill 2\\n• Missing skill 3",
  "reasoning": "one sentence summary"
}}

Score 1.0 = perfect match, 0.0 = completely wrong role.
"""
        try:
            resp = _client().models.generate_content(model=_MODEL, contents=prompt)
            text = resp.text.strip().strip("```json").strip("```").strip()
            data = json.loads(text)
            llm_score = float(max(0.0, min(1.0, data.get("score", 0.5))))
            gap_analysis = data.get("gap_analysis", "")
        except Exception as e:
            print(f"[matcher] LLM error: {e}")

    composite = round(0.3 * kw_score + 0.3 * sem_score + 0.4 * llm_score, 4)
    return {
        "keyword_score": round(kw_score, 4),
        "semantic_score": round(sem_score, 4),
        "llm_score": round(llm_score, 4),
        "composite_score": composite,
        "gap_analysis": gap_analysis,
    }
