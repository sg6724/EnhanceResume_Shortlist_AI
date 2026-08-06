from __future__ import annotations

import re

from ..config import settings
from ..services.llm import generate

# gemini-2.0-flash was removed from the Gemini free tier (429 "limit: 0").
# Rewriting LaTeX needs capability, so use the full flash model.
_MODEL = "gemini-2.5-flash"
_GROQ_MODEL = "llama-3.3-70b-versatile"


def _extract_environments(tex: str) -> frozenset[str]:
    """Return the set of LaTeX environments present in the tex."""
    return frozenset(re.findall(r"\\begin\{([^}]+)\}", tex))


async def rewrite_resume(
    master_tex: str,
    jd_text: str,
    gap_analysis: str,
    position_context: str,
    attempt: int = 1,
    previous_error: str = "",
) -> tuple[str, str]:
    """
    Rewrite the master .tex for a specific JD.
    Returns (rewritten_tex, diff_summary_text).
    Raises ValueError if LaTeX environment structure was changed.
    Falls back to returning master unchanged if no API key.
    """
    if not settings.gemini_api_key and not settings.groq_api_key:
        return master_tex, "No GEMINI_API_KEY or GROQ_API_KEY — master returned unchanged"

    error_context = (
        f"\n\nPrevious pdflatex compile error (attempt {attempt}):\n{previous_error[:1000]}"
        if previous_error else ""
    )

    prompt = f"""You are an expert LaTeX resume writer.
You will tailor the given resume for a specific job by editing a COPY of it.

ABSOLUTE RULES — breaking any of these means the output is invalid:
1. NEVER add or delete \\begin{{...}}...\\end{{...}} blocks. Only edit content inside them.
2. NEVER change the document preamble (\\documentclass, \\usepackage, etc.).
3. Use ONLY LaTeX commands that are valid with the existing packages.
4. Return ONLY the complete modified .tex file, then on a new line write "DIFF:" followed by a brief bullet summary.
5. TRUTHFULNESS: ONLY use skills, employers, job titles, degrees, certifications, projects, and metrics that ALREADY appear in the MASTER RESUME. Never invent, fabricate, exaggerate, or add any experience, employer, role, degree, certification, tool, framework, programming language, or quantifiable metric (e.g. "improved X by 40%") that is not present in the master resume. To address a JD requirement you lack, rephrase or emphasize EXISTING experience - never create new claims.

Target position: {position_context}

Skills/experience gaps to address:
{gap_analysis}

Job description (use this to understand what to emphasize):
{jd_text[:2000]}
{error_context}

Master resume (ONLY edit content inside existing environments):
{master_tex}
"""

    full_response = await generate(prompt, gemini_model=_MODEL, groq_model=_GROQ_MODEL)

    # Split on "DIFF:" marker
    if "DIFF:" in full_response:
        parts = full_response.split("DIFF:", 1)
        rewritten = parts[0].strip()
        diff_summary = "DIFF:\n" + parts[1].strip()
    else:
        rewritten = full_response.strip()
        diff_summary = "Agent did not provide a diff summary."

    # Strip markdown fences if the model wrapped the tex
    if rewritten.startswith("```"):
        rewritten = re.sub(r"^```[a-zA-Z]*\n?", "", rewritten)
        rewritten = re.sub(r"\n?```$", "", rewritten.strip())

    # Strip any conversational preamble the model prepended before the tex
    # (e.g. "Here is the modified resume:") — pdflatex fails with "Missing
    # \begin{document}" on stray text before \documentclass, even though it
    # doesn't change the environment set the check below looks for.
    doc_start = rewritten.find("\\documentclass")
    if doc_start > 0:
        rewritten = rewritten[doc_start:]

    # Validate: LaTeX environment structure must be unchanged
    orig_envs = _extract_environments(master_tex)
    new_envs = _extract_environments(rewritten)
    if orig_envs != new_envs:
        added = new_envs - orig_envs
        removed = orig_envs - new_envs
        raise ValueError(
            f"LaTeX structure violation — environments changed. "
            f"Added: {added or 'none'}, Removed: {removed or 'none'}"
        )

    return rewritten, diff_summary
