from __future__ import annotations

import json

from google import genai

from ..config import settings

_MODEL = "gemini-2.0-flash"


def _client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


async def is_jd_relevant(jd_text: str, target_titles: list[str]) -> tuple[bool, str]:
    """
    Fast LLM gate: is this JD relevant to any of the target positions?
    Returns (is_relevant, reasoning).
    Falls back to True if no API key (let the matcher decide).
    """
    if not settings.gemini_api_key:
        return True, "no GEMINI_API_KEY — defaulting to pass"

    titles_str = ", ".join(f'"{t}"' for t in target_titles)
    prompt = f"""You are a senior recruiter screening job descriptions.
The candidate is targeting: {titles_str}

Job description excerpt:
{jd_text[:2500]}

Answer in valid JSON only, no markdown fences:
{{"relevant": true_or_false, "reason": "one sentence"}}

A JD is relevant if the core role aligns with at least one target position.
A JD is NOT relevant if the role is fundamentally different (e.g., Sales Manager vs AI Engineer).
"""
    try:
        resp = _client().models.generate_content(model=_MODEL, contents=prompt)
        text = resp.text.strip().strip("```json").strip("```").strip()
        data = json.loads(text)
        return bool(data.get("relevant", True)), data.get("reason", "")
    except Exception as e:
        print(f"[filter] LLM error: {e} — defaulting to pass")
        return True, f"filter error: {e}"
