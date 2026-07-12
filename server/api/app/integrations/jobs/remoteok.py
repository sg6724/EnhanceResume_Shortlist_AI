from __future__ import annotations

import asyncio
import re

import httpx

from ...domain.models import RawJd

_GENERIC_ROLE_TOKENS = {
    "engineer", "engineering", "developer", "dev", "scientist", "analyst",
    "specialist", "manager", "lead", "senior", "junior", "staff", "principal",
    "sr", "jr", "intern", "the", "of", "and", "a", "an",
}


def _tokens(text: str) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9]+", text.lower()) if w]


def _remoteok_tags(keywords: list[str], limit: int = 5) -> list[str]:
    """RemoteOK uses short single-word tags (e.g. 'ai', 'ml'), so expand each
    keyword into candidate tags: its hyphen-slug plus each specific
    (non-generic) token. Unknown tags simply return no jobs and are harmless."""
    tags: list[str] = []
    seen: set[str] = set()
    for kw in keywords:
        toks = _tokens(kw)
        if not toks:
            continue
        candidates = ["-".join(toks)] + [t for t in toks if t not in _GENERIC_ROLE_TOKENS]
        for c in candidates:
            if c and c not in seen:
                seen.add(c)
                tags.append(c)
    return tags[:limit]


class RemoteOkSource:
    """RemoteOK public API job source. The httpx client is injected so tests
    can substitute `httpx.MockTransport` instead of hitting the real network."""

    def __init__(self, http: httpx.AsyncClient, sleep_seconds: float = 1.5):
        self._http = http
        self._sleep_seconds = sleep_seconds

    async def fetch(self, keywords: list[str]) -> list[RawJd]:
        results: list[RawJd] = []
        seen_ids: set[str] = set()
        for tag in _remoteok_tags(keywords):
            try:
                resp = await self._http.get(
                    f"https://remoteok.com/api?tag={tag}",
                    headers={"User-Agent": "Mozilla/5.0 JobHuntBot/1.0"},
                    timeout=20.0,
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                for job in (data[1:] if isinstance(data, list) else []):
                    if not isinstance(job, dict) or "position" not in job:
                        continue
                    jid = str(job.get("id") or job.get("slug") or job.get("url"))
                    if jid in seen_ids:
                        continue
                    seen_ids.add(jid)
                    tags_list = job.get("tags") or []
                    results.append(RawJd(
                        source="remoteok",
                        company=job.get("company", "Unknown"),
                        title=job.get("position", tag),
                        location=job.get("location") or "Remote",
                        url=job.get("url", ""),
                        raw_text=(
                            f"{job.get('position', '')} at {job.get('company', '')}\n\n"
                            f"Tags: {', '.join(tags_list)}\n\n"
                            f"{job.get('description') or ''}"
                        ),
                    ))
            except Exception:
                continue
            if self._sleep_seconds:
                await asyncio.sleep(self._sleep_seconds)
        return results
