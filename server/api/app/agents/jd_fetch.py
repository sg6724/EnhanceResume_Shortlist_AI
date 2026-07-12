from __future__ import annotations

import json
import re
from html import unescape

import httpx
from bs4 import BeautifulSoup

from ..config import settings
from ..services.llm import generate

_MODEL = "gemini-2.0-flash"
_GROQ_MODEL = "llama-3.1-8b-instant"

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


async def fetch_jd_from_url(http: httpx.AsyncClient, url: str) -> dict:
    """Fetch a job posting URL and extract company/title/JD text.

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
        return {
            "company": posting["company"],
            "title": posting["title"],
            "jd_text": posting["description"],
            "source": "jsonld",
            "possibly_closed": _detect_closed_posting(posting["description"]),
        }

    visible_text = _extract_visible_text(html_text)
    if not visible_text.strip():
        return {"error": "that page returned no readable text"}

    extracted = await _llm_extract_jd(visible_text)
    if not extracted["jd_text"]:
        return {"error": "could not find a job description on that page — try pasting the JD text directly"}

    return {
        "company": extracted["company"],
        "title": extracted["title"],
        "jd_text": extracted["jd_text"],
        "source": "llm_extracted",
        "possibly_closed": _detect_closed_posting(visible_text),
    }
