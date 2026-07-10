from __future__ import annotations

import json
import re

import httpx
from bs4 import BeautifulSoup

from ...domain.models import Contact
from ..llm.base import LlmClient

_COMPANY_SUFFIX_RE = re.compile(
    r"\b(inc|llc|ltd|limited|corp|corporation|pvt|private|co)\b\.?", re.IGNORECASE,
)
_TEAM_PATHS = ["/about", "/team", "/about-us", "/company"]
LEADER_TITLE_RE = re.compile(
    r"\b(cto|chief technology officer|co[\s-]?founder|founder|(head|vp) of engineering)\b",
    re.IGNORECASE,
)
_MODEL = "gemini-2.5-flash"


def candidate_domains(company_name: str) -> list[str]:
    """Guess likely domains from a company name: acmelabs.com/.io/.ai."""
    base = _COMPANY_SUFFIX_RE.sub("", company_name.lower())
    slug = re.sub(r"[^a-z0-9]", "", base)
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


def _domain_page_matches(token: str, title: str | None) -> bool:
    if len(token) < 4:
        return False
    normalized_title = re.sub(r"[^a-z0-9]", "", (title or "").lower())
    return token in normalized_title


class SiteScrapeProvider:
    """Fallback contact provider: guess the company domain, scrape team/about
    pages, ask the LLM to extract leadership, then pattern-guess an email.
    Ported from the pre-refactor `agents/contact_finder.py` — same behavior,
    now behind the ContactProvider protocol with the LLM and HTTP client
    injected instead of self-constructed."""

    def __init__(self, http: httpx.AsyncClient, llm: LlmClient):
        self._http = http
        self._llm = llm

    async def _resolve_domain(self, company_name: str) -> str | None:
        token = re.sub(r"[^a-z0-9]", "", _COMPANY_SUFFIX_RE.sub("", company_name.lower()))
        for domain in candidate_domains(company_name):
            try:
                resp = await self._http.get(f"https://{domain}", follow_redirects=True, timeout=10.0)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                title = soup.title.string if soup.title else None
                if _domain_page_matches(token, title):
                    return domain
            except Exception:
                continue
        return None

    async def _scrape_team_pages(self, domain: str) -> str:
        chunks: list[str] = []
        for path in _TEAM_PATHS:
            try:
                resp = await self._http.get(f"https://{domain}{path}", follow_redirects=True, timeout=10.0)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer"]):
                    tag.decompose()
                chunks.append(soup.get_text(" ", strip=True)[:4000])
            except Exception:
                continue
        return "\n".join(chunks)[:10000]

    async def _extract_leaders(self, page_text: str, company_name: str) -> list[dict]:
        if not page_text.strip():
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
            text = await self._llm.generate(_MODEL, prompt)
            text = text.strip().strip("```json").strip("```").strip()
            people = json.loads(text).get("people", [])
            return [p for p in people if p.get("name") and LEADER_TITLE_RE.search(p.get("title", ""))]
        except Exception:
            return []

    async def find(self, company_name: str, company_domain: str | None, titles: list[str]) -> Contact | None:
        domain = company_domain or await self._resolve_domain(company_name)
        if not domain:
            return None
        page_text = await self._scrape_team_pages(domain)
        leaders = await self._extract_leaders(page_text, company_name)
        if not leaders:
            return None
        name_parts = leaders[0]["name"].split()
        first = name_parts[0]
        last = name_parts[-1] if len(name_parts) > 1 else ""
        guesses = guess_emails(first, last, domain)
        if not guesses:
            return None
        return Contact(
            company_domain=domain,
            founder_name=leaders[0]["name"],
            founder_title=leaders[0]["title"],
            founder_email=guesses[0],
            email_confidence="guessed",
            contact_method="scraped",
        )
