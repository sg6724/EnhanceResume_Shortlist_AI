from __future__ import annotations

import json
import re
from html import unescape

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from ..config import settings
from ..services.llm import generate, get_client

_MODEL = "gemini-2.0-flash"
_GROQ_MODEL = "llama-3.3-70b-versatile"
# url_context requires 2.5-flash — not available on 2.0-flash.
_URL_CONTEXT_MODEL = "gemini-2.5-flash"

_JSONLD_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)

_CLOSED_PATTERNS = re.compile(
    r"has been filled|no longer available|posting has expired|"
    r"position has been filled|this position is closed|job.{0,15}has been filled",
    re.IGNORECASE,
)

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _clean_html_fragment(fragment: str) -> str:
    """Unescape HTML entities (JSON-LD description fields are HTML-escaped),
    then strip any remaining tags, returning plain text."""
    return BeautifulSoup(unescape(fragment), "html.parser").get_text(" ", strip=True)


def _extract_jsonld_jobposting(html_text: str) -> dict | None:
    """Find the first schema.org JobPosting JSON-LD block, if any.

    Returns {"title", "company", "description", "location"} (description
    already cleaned to plain text) or None if no matching, parseable block
    is found.
    """
    for block in _JSONLD_RE.findall(html_text):
        try:
            data = json.loads(block)
        except (json.JSONDecodeError, ValueError):
            continue
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if not isinstance(item, dict) or item.get("@type") != "JobPosting":
                continue
            description = item.get("description") or ""
            hiring_org = item.get("hiringOrganization") or {}
            job_loc = item.get("jobLocation") or {}
            address = job_loc.get("address") or {}
            location_parts = [
                address.get(k) for k in ("addressLocality", "addressRegion", "addressCountry")
            ]
            return {
                "title": item.get("title") or "",
                "company": hiring_org.get("name") or "",
                "description": _clean_html_fragment(description) if description else "",
                "location": ", ".join(p for p in location_parts if p),
            }
    return None


def _extract_visible_text(html_text: str, max_chars: int = 4000) -> str:
    """Strip script/style/nav/footer/noscript and return the remaining
    visible text, capped to max_chars."""
    soup = BeautifulSoup(html_text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "noscript"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)[:max_chars]


def _detect_closed_posting(text: str) -> bool:
    return bool(_CLOSED_PATTERNS.search(text))


async def _llm_extract_jd(page_text: str) -> dict:
    """Fallback extraction for pages with no JobPosting JSON-LD (e.g. a
    LinkedIn hiring post, a blog-style announcement). Returns
    {"company", "title", "jd_text"}, all empty strings if extraction
    isn't possible or no LLM key is configured."""
    empty = {"company": "", "title": "", "jd_text": ""}
    if not settings.gemini_api_key and not settings.groq_api_key:
        return empty
    prompt = f"""You are extracting a job posting from scraped web page text.
Ignore site boilerplate: cookie notices, login/signup prompts, navigation menus.

Page text:
{page_text}

Answer in valid JSON only, no markdown fences:
{{"company": "company name", "title": "job title", "jd_text": "the full job description and requirements, cleaned of boilerplate"}}
If you cannot find a real job posting in this text, return {{"company": "", "title": "", "jd_text": ""}}."""
    try:
        raw = await generate(prompt, gemini_model=_MODEL, groq_model=_GROQ_MODEL)
        text = raw.strip().strip("```json").strip("```").strip()
        data = json.loads(text)
        return {
            "company": data.get("company") or "",
            "title": data.get("title") or "",
            "jd_text": data.get("jd_text") or "",
        }
    except Exception as e:
        print(f"[jd_fetch] LLM extraction error: {e}")
        return empty


async def _fetch_via_url_context(url: str) -> dict:
    """Fallback fetch using Gemini's url_context server-side tool.

    url_context is still a server-side fetcher, not a real browser — sites
    with real anti-bot fingerprinting (LinkedIn) block it the same way they
    block a plain httpx GET. This only helps sites that reject generic
    scripted requests without full bot detection (many ATS/career pages).
    Returns {"company", "title", "jd_text"}, all empty on any failure.
    """
    empty = {"company": "", "title": "", "jd_text": ""}
    if not settings.gemini_api_key:
        return empty
    from google.genai.types import GenerateContentConfig

    prompt = f"""Fetch the job posting at this URL and extract its details: {url}
Ignore site boilerplate: cookie notices, login/signup prompts, navigation menus.

Answer in valid JSON only, no markdown fences:
{{"company": "company name", "title": "job title", "jd_text": "the full job description and requirements, cleaned of boilerplate"}}
If you cannot access the page or find no real job posting, return {{"company": "", "title": "", "jd_text": ""}}."""
    try:
        resp = await get_client().aio.models.generate_content(
            model=_URL_CONTEXT_MODEL,
            contents=prompt,
            config=GenerateContentConfig(tools=[{"url_context": {}}]),
        )
        text = (resp.text or "").strip().strip("```json").strip("```").strip()
        data = json.loads(text)
        return {
            "company": data.get("company") or "",
            "title": data.get("title") or "",
            "jd_text": data.get("jd_text") or "",
        }
    except Exception as e:
        print(f"[jd_fetch] url_context fetch error: {e}")
        return empty


async def _fetch_via_httpx(http: httpx.AsyncClient, url: str) -> dict:
    """Fetch a job posting URL and extract company/title/JD text via a plain
    HTTP GET.

    Tries a JobPosting JSON-LD block first (free, covers most ATS
    platforms); falls back to visible-text + one LLM extraction call
    for unstructured pages (e.g. a LinkedIn hiring post).

    Returns {"company", "title", "jd_text", "source", "possibly_closed"}
    on success, or {"error": str} on any fetch failure.
    """
    try:
        resp = await http.get(url, headers={"User-Agent": _BROWSER_UA}, follow_redirects=True, timeout=15.0)
    except Exception as e:
        return {"error": f"could not reach that URL: {e}"}
    if resp.status_code != 200:
        return {"error": f"URL returned status {resp.status_code}"}

    html_text = resp.text
    posting = _extract_jsonld_jobposting(html_text)
    if posting and posting.get("description"):
        # JSON-LD metadata can be stale (a closed/filled posting's JSON-LD
        # still describes the original opening) — the "this job has been
        # filled" banner only shows up in the page's live rendered chrome,
        # not in the description field itself, so check both.
        possibly_closed = (
            _detect_closed_posting(posting["description"])
            or _detect_closed_posting(_extract_visible_text(html_text, max_chars=1000))
        )
        struct = await extract_jd_structured(posting["description"])
        return {
            "company": posting["company"],
            "title": posting["title"],
            "jd_text": posting["description"],
            "source": "jsonld",
            "possibly_closed": possibly_closed,
            "role_title": struct.role_title or posting["title"],
            "seniority": struct.seniority,
            "responsibilities": struct.responsibilities,
            "must_have_skills": struct.must_have_skills,
            "nice_to_have_skills": struct.nice_to_have_skills,
            "tech_stack": struct.tech_stack,
        }

    visible_text = _extract_visible_text(html_text)
    if not visible_text.strip():
        return {"error": "that page returned no readable text"}

    extracted = await _llm_extract_jd(visible_text)
    if not extracted["jd_text"]:
        return {"error": "could not find a job description on that page — try pasting the JD text directly"}

    struct = await extract_jd_structured(extracted["jd_text"])
    return {
        "company": extracted["company"],
        "title": extracted["title"],
        "jd_text": extracted["jd_text"],
        "source": "llm_extracted",
        "possibly_closed": _detect_closed_posting(visible_text),
        "role_title": struct.role_title or extracted["title"],
        "seniority": struct.seniority,
        "responsibilities": struct.responsibilities,
        "must_have_skills": struct.must_have_skills,
        "nice_to_have_skills": struct.nice_to_have_skills,
        "tech_stack": struct.tech_stack,
    }


async def fetch_jd_from_url(http: httpx.AsyncClient, url: str) -> dict:
    """Fetch a job posting URL and extract company/title/JD text.

    Tries a plain HTTP GET first (JSON-LD, then visible-text + LLM
    extraction — see `_fetch_via_httpx`). If that fails outright, falls back
    to Gemini's url_context tool, which fetches server-side and succeeds on
    some sites a generic scripted GET gets blocked on (though not on sites
    with real anti-bot fingerprinting, like LinkedIn — see
    `_fetch_via_url_context`).

    Returns {"company", "title", "jd_text", "source", "possibly_closed", ...}
    on success, or {"error": str} if every path fails.
    """
    result = await _fetch_via_httpx(http, url)
    if "error" not in result:
        return result

    httpx_error = result["error"]
    fallback = await _fetch_via_url_context(url)
    if not fallback["jd_text"]:
        return {"error": httpx_error}

    struct = await extract_jd_structured(fallback["jd_text"])
    return {
        "company": fallback["company"],
        "title": fallback["title"],
        "jd_text": fallback["jd_text"],
        "source": "url_context",
        "possibly_closed": _detect_closed_posting(fallback["jd_text"]),
        "role_title": struct.role_title or fallback["title"],
        "seniority": struct.seniority,
        "responsibilities": struct.responsibilities,
        "must_have_skills": struct.must_have_skills,
        "nice_to_have_skills": struct.nice_to_have_skills,
        "tech_stack": struct.tech_stack,
    }


class ExtractedJD(BaseModel):
    """Structured, normalized job description per the platform spec.

    Mirrors the spec's extraction schema: company, role_title, seniority,
    responsibilities, must_have_skills, nice_to_have_skills, tech_stack, and the
    raw text. All fields have safe defaults so a failed/empty extraction never
    crashes the caller (Python equivalent of the spec's zod/joi validation).
    """

    company: str = ""
    role_title: str = ""
    seniority: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    must_have_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    raw_jd_text: str = ""


async def extract_jd_structured(raw_jd_text: str) -> ExtractedJD:
    """Extract the structured JD schema from raw JD text via one Gemini call.

    Returns an ``ExtractedJD`` with sane defaults on any failure (no API key,
    malformed JSON, network error) so callers can persist gracefully. Only
    includes skills/technologies explicitly stated in the JD.
    """
    if not settings.gemini_api_key and not settings.groq_api_key:
        return ExtractedJD(raw_jd_text=raw_jd_text or "")
    if not raw_jd_text or not raw_jd_text.strip():
        return ExtractedJD()

    prompt = f"""You are extracting structured data from a job description.
Ignore site boilerplate: cookie notices, navigation menus, login/signup prompts.

Job description:
{raw_jd_text[:6000]}

Respond in valid JSON only, no markdown fences:
{{
  "company": "company name",
  "role_title": "exact job title",
  "seniority": "junior|mid|senior|staff|lead|principal|manager|director|executive|unknown",
  "responsibilities": ["responsibility 1", "responsibility 2"],
  "must_have_skills": ["required skill 1", "required skill 2"],
  "nice_to_have_skills": ["preferred skill 1"],
  "tech_stack": ["technology 1", "technology 2"]
}}
Only include skills/technologies explicitly stated in the JD. If a field is absent, use an empty string or empty list.
"""
    try:
        raw = await generate(prompt, gemini_model=_MODEL, groq_model=_GROQ_MODEL)
        text = raw.strip().strip("```json").strip("```").strip()
        data = json.loads(text)
        return ExtractedJD(
            company=str(data.get("company") or ""),
            role_title=str(data.get("role_title") or ""),
            seniority=str(data.get("seniority") or ""),
            responsibilities=[str(x) for x in (data.get("responsibilities") or []) if x],
            must_have_skills=[str(x) for x in (data.get("must_have_skills") or []) if x],
            nice_to_have_skills=[str(x) for x in (data.get("nice_to_have_skills") or []) if x],
            tech_stack=[str(x) for x in (data.get("tech_stack") or []) if x],
            raw_jd_text=raw_jd_text,
        )
    except Exception as e:
        print(f"[jd_fetch] structured extraction error: {e}")
        return ExtractedJD(raw_jd_text=raw_jd_text)
