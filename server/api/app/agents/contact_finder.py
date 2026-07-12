from __future__ import annotations

import json
import re

import httpx

from ..config import settings
from ..services.llm import generate
from ..services.hunter import (
    hunter_domain_search,
    hunter_quota_remaining,
    increment_hunter_quota,
    pick_leader,
    LEADER_TITLE_RE,
)

_COMPANY_SUFFIX_RE = re.compile(
    r"\b(inc|llc|ltd|limited|corp|corporation|pvt|private|co)\b\.?",
    re.IGNORECASE,
)
_TEAM_PATHS = ["/about", "/team", "/about-us", "/company"]
_MODEL = "gemini-2.5-flash"
_GROQ_MODEL = "llama-3.3-70b-versatile"


def candidate_domains(company_name: str) -> list[str]:
    """Guess likely domains from a company name: acmelabs.com/.io/.ai."""
    base = _COMPANY_SUFFIX_RE.sub("", company_name.lower())
    slug = re.sub(r"[^a-z0-9]", "", base)
    # Keep well-known compound names intact minus legal suffixes; fall back to first word
    if not slug:
        return []
    return [f"{slug}.com", f"{slug}.io", f"{slug}.ai"]


def guess_emails(first: str, last: str, domain: str) -> list[str]:
    """Common startup email patterns, most likely first."""
    f, l = first.strip().lower(), last.strip().lower()
    if not f:
        return []
    if not l:
        return [f"{f}@{domain}"]
    return [f"{f}@{domain}", f"{f}.{l}@{domain}", f"{f[0]}{l}@{domain}"]


def _domain_page_matches(token: str, title: str | None, page_text: str) -> bool:
    """Decide whether a fetched homepage plausibly belongs to `company_name`.

    Short tokens (e.g. "zip", "ai", "co") are common for startup slugs but are
    also common English substrings, so an arbitrary substring match against
    the whole page body produces false positives on nearly any live site.
    Require a minimum token length, and then require the token to appear in
    the page `<title>` (a much stronger, more specific signal than anywhere
    in the body text).
    """
    if len(token) < 4:
        return False
    normalized_title = re.sub(r"[^a-z0-9]", "", (title or "").lower())
    return token in normalized_title


async def _resolve_domain(http: httpx.AsyncClient, company_name: str) -> str | None:
    """Try candidate domains; accept the first whose homepage <title> mentions the company."""
    from bs4 import BeautifulSoup

    token = re.sub(r"[^a-z0-9]", "", _COMPANY_SUFFIX_RE.sub("", company_name.lower()))
    for domain in candidate_domains(company_name):
        try:
            resp = await http.get(f"https://{domain}", follow_redirects=True, timeout=10.0)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.string if soup.title else None
            if _domain_page_matches(token, title, resp.text.lower()):
                return domain
        except Exception:
            continue
    return None


async def _scrape_team_pages(http: httpx.AsyncClient, domain: str) -> str:
    """Concatenate visible text of about/team pages (capped)."""
    from bs4 import BeautifulSoup

    chunks: list[str] = []
    for path in _TEAM_PATHS:
        try:
            resp = await http.get(f"https://{domain}{path}", follow_redirects=True, timeout=10.0)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            chunks.append(soup.get_text(" ", strip=True)[:4000])
        except Exception:
            continue
    return "\n".join(chunks)[:10000]


async def _extract_leaders(page_text: str, company_name: str) -> list[dict]:
    """Gemini 2.5 Flash (Groq fallback): extract [{name, title}] leadership from page text."""
    no_provider = not settings.gemini_api_key and not settings.groq_api_key
    if no_provider or not page_text.strip():
        return []
    prompt = f"""Extract the technical leadership of "{company_name}" from this website text.
Only include people whose title is CTO, founder, co-founder, chief technology officer,
head of engineering, or VP of engineering.

Website text:
{page_text}

Answer in valid JSON only, no markdown fences:
{{"people": [{{"name": "Full Name", "title": "their title"}}]}}
If none found, return {{"people": []}}."""
    try:
        raw = await generate(prompt, gemini_model=_MODEL, groq_model=_GROQ_MODEL)
        text = raw.strip().strip("```json").strip("```").strip()
        people = json.loads(text).get("people", [])
        return [p for p in people if p.get("name") and LEADER_TITLE_RE.search(p.get("title", ""))]
    except Exception as e:
        print(f"[contact_finder] extraction error: {e}")
        return []


async def find_contact(
    http: httpx.AsyncClient, sb, company_name: str, company_domain: str | None
) -> dict:
    """Hunter first (quota permitting), then scrape + pattern-guess fallback."""
    domain = company_domain or await _resolve_domain(http, company_name)
    if not domain:
        return {"found": False, "company_domain": None,
                "failure_reason": "could not resolve company domain"}

    # 1) Hunter (verified emails), only while free-tier quota remains
    if settings.hunter_api_key and await hunter_quota_remaining(sb) > 0:
        emails = await hunter_domain_search(http, domain)
        await increment_hunter_quota(sb)
        leader = pick_leader(emails)
        if leader:
            name = f"{leader.get('first_name', '')} {leader.get('last_name', '')}".strip()
            return {"found": True, "company_domain": domain,
                    "founder_name": name or "there",
                    "founder_title": leader.get("position", ""),
                    "founder_email": leader["value"],
                    "email_confidence": "verified",
                    "contact_method": "hunter"}

    # 2) Scrape fallback: team pages -> Gemini -> pattern guess
    page_text = await _scrape_team_pages(http, domain)
    leaders = await _extract_leaders(page_text, company_name)
    if leaders:
        name_parts = leaders[0]["name"].split()
        first = name_parts[0]
        last = name_parts[-1] if len(name_parts) > 1 else ""
        guesses = guess_emails(first, last, domain)
        if guesses:
            return {"found": True, "company_domain": domain,
                    "founder_name": leaders[0]["name"],
                    "founder_title": leaders[0]["title"],
                    "founder_email": guesses[0],
                    "email_confidence": "guessed",
                    "contact_method": "scraped"}

    return {"found": False, "company_domain": domain,
            "failure_reason": "no CTO/founder found via Hunter or site scrape"}
