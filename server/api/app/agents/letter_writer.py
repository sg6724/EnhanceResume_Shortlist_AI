from __future__ import annotations

import json

from ..config import settings
from ..services.llm import generate

_MODEL = "gemini-2.5-flash"
_GROQ_MODEL = "llama-3.3-70b-versatile"

BANNED_PHRASES = [
    "i hope this email finds you well",
    "i hope this finds you well",
    "to whom it may concern",
    "dear sir",
    "dear madam",
    "i am writing to express",
]
MAX_WORDS = 420


def validate_letter(subject: str, body: str) -> str | None:
    """Return an error message, or None when the letter meets constraints."""
    if not subject.strip():
        return "empty subject"
    if not body.strip():
        return "empty body"
    words = len(body.split())
    if words > MAX_WORDS:
        return f"body too long: {words} words (max {MAX_WORDS})"
    lowered = body.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lowered:
            return f"banned phrase: '{phrase}'"
    return None


async def write_letter(
    resume_text: str,
    jd_text: str,
    role_title: str,
    founder_name: str,
    founder_title: str,
    company_name: str,
) -> tuple[str, str]:
    """Compatibility wrapper for older callers."""
    return await write_application_cover_letter(
        resume_text=resume_text,
        jd_text=jd_text,
        role_title=role_title,
        company_name=company_name,
    )


async def write_application_cover_letter(
    resume_text: str,
    jd_text: str,
    role_title: str,
    company_name: str,
) -> tuple[str, str]:
    """Gemini/Groq drafts a job-application cover letter. Returns (subject, body)."""
    if not settings.gemini_api_key and not settings.groq_api_key:
        raise ValueError("GEMINI_API_KEY or GROQ_API_KEY not configured")

    jd_block = f"Job description:\n{jd_text[:3000]}" if jd_text.strip() else \
        "No job description available; tailor to the role title directly."

    last_error = ""
    for attempt in range(2):
        strictness = "" if attempt == 0 else \
            f"\nYour previous draft was rejected: {last_error}. Fix that exactly."
        prompt = f"""Write a concise cover letter for a job application to {company_name} for the role of {role_title}.

Candidate resume:
{resume_text[:4000]}

{jd_block}

Rules:
- 250-380 words. Hard maximum 420 words.
- Professional, direct tone.
- First paragraph states role fit clearly.
- Use 2-4 concrete proof points from the resume that map to the JD requirements.
- Mention the company and role naturally.
- Close with availability/interest in next steps.
- NO filler: never open with pleasantries like "I hope this finds you well".
- Do not invent degrees, employers, metrics, certifications, or tools not present in the resume/JD.{strictness}

Answer in valid JSON only, no markdown fences:
{{"subject": "...", "body": "..."}}"""
        raw = await generate(prompt, gemini_model=_MODEL, groq_model=_GROQ_MODEL)
        text = raw.strip().strip("```json").strip("```").strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            last_error = f"invalid JSON: {e}"
            continue
        subject, body = data.get("subject", ""), data.get("body", "")
        err = validate_letter(subject, body)
        if err is None:
            return subject, body
        last_error = err

    raise ValueError(f"letter generation failed after 2 attempts: {last_error}")
