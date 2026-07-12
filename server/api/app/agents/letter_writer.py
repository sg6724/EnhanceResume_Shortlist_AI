from __future__ import annotations

import json

from ..config import settings
from ..services.llm import get_client

_MODEL = "gemini-2.5-flash"

BANNED_PHRASES = [
    "i hope this email finds you well",
    "i hope this finds you well",
    "to whom it may concern",
    "dear sir",
    "dear madam",
    "i am writing to express",
]
MAX_WORDS = 220


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
    """Gemini 2.5 Flash drafts a direct cover-letter email. Returns (subject, body)."""
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY not configured")

    jd_block = f"Job description:\n{jd_text[:3000]}" if jd_text.strip() else \
        "No job description available — pitch for the role title directly."

    last_error = ""
    for attempt in range(2):
        strictness = "" if attempt == 0 else \
            f"\nYour previous draft was rejected: {last_error}. Fix that exactly."
        prompt = f"""Write a short, direct cold email from a job seeker to {founder_name} ({founder_title}) at {company_name}, asking to be considered for the role of {role_title}.

Candidate resume:
{resume_text[:4000]}

{jd_block}

Rules:
- 120-180 words. Hard maximum 200 words.
- Direct tone. First line states who the candidate is in one sentence.
- 2-3 concrete proof points from the resume that map to the company's stack/needs.
- Clear ask: consideration for the {role_title} role. Mention the resume is attached.
- NO filler: never open with pleasantries like "I hope this finds you well".
- Address {founder_name} by first name.{strictness}

Answer in valid JSON only, no markdown fences:
{{"subject": "...", "body": "..."}}"""
        resp = await get_client().aio.models.generate_content(model=_MODEL, contents=prompt)
        text = resp.text.strip().strip("```json").strip("```").strip()
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
