from __future__ import annotations

import asyncio
import hashlib
import re
from typing import Any

import aiohttp

from ..config import settings

# Max candidate JDs kept after dedup/validation. Each candidate later costs
# several (free-tier, rate-limited) Gemini calls in the filter+match stages,
# so keep the pool small.
MAX_CANDIDATES = 20

# Generic role words that are useless as RemoteOK tags — tag=engineer pulls a
# huge, mostly-irrelevant pool. We drop these when a more specific token exists.
_GENERIC_ROLE_TOKENS = {
    "engineer", "engineering", "developer", "dev", "scientist", "analyst",
    "specialist", "manager", "lead", "senior", "junior", "staff", "principal",
    "sr", "jr", "intern", "the", "of", "and", "a", "an",
}


def _tokens(text: str) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9]+", text.lower()) if w]


def _remoteok_tags(keywords: list[str], limit: int = 5) -> list[str]:
    """RemoteOK uses short single-word tags (e.g. 'ai', 'ml'), so expand each
    keyword into candidate tags: its hyphen-slug plus each specific (non-generic)
    token. Unknown tags simply return no jobs and are harmless."""
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


async def _fetch_remoteok(keywords: list[str]) -> list[dict[str, Any]]:
    """RemoteOK public API — completely free, no auth required."""
    results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    async with aiohttp.ClientSession() as session:
        for tag in _remoteok_tags(keywords):
            url = f"https://remoteok.com/api?tag={tag}"
            try:
                async with session.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 GetHiredBot/1.0"},
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json(content_type=None)
                    # First element is a legal notice dict, skip it
                    for job in (data[1:] if isinstance(data, list) else []):
                        if not isinstance(job, dict) or "position" not in job:
                            continue
                        jid = str(job.get("id") or job.get("slug") or job.get("url"))
                        if jid in seen_ids:
                            continue
                        seen_ids.add(jid)
                        desc = job.get("description") or ""
                        tags_list = job.get("tags") or []
                        results.append({
                            "source": "remoteok",
                            "company": job.get("company", "Unknown"),
                            "title": job.get("position", tag),
                            "location": job.get("location") or "Remote",
                            "url": job.get("url", ""),
                            "raw_text": (
                                f"{job.get('position', '')} at {job.get('company', '')}\n\n"
                                f"Tags: {', '.join(tags_list)}\n\n"
                                f"{desc}"
                            ),
                        })
            except Exception as e:
                print(f"[scraper] RemoteOK error for tag '{tag}': {e}")
            await asyncio.sleep(1.5)  # respect rate limits
    return results


async def _fetch_adzuna(keywords: list[str]) -> list[dict[str, Any]]:
    """Adzuna API — free tier: developer.adzuna.com"""
    if not settings.adzuna_app_id or not settings.adzuna_api_key:
        return []
    results: list[dict[str, Any]] = []
    async with aiohttp.ClientSession() as session:
        for kw in keywords[:3]:
            url = (
                f"https://api.adzuna.com/v1/api/jobs/in/search/1"
                f"?app_id={settings.adzuna_app_id}"
                f"&app_key={settings.adzuna_api_key}"
                f"&results_per_page=20"
                f"&what={kw.replace(' ', '%20')}"
                f"&content-type=application/json"
            )
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for job in data.get("results", []):
                            results.append({
                                "source": "adzuna",
                                "company": job.get("company", {}).get("display_name", "Unknown"),
                                "title": job.get("title", kw),
                                "location": job.get("location", {}).get("display_name", ""),
                                "url": job.get("redirect_url", ""),
                                "raw_text": (
                                    f"{job.get('title', '')} at "
                                    f"{job.get('company', {}).get('display_name', '')}\n\n"
                                    f"{job.get('description', '')}"
                                ),
                            })
            except Exception as e:
                print(f"[scraper] Adzuna error for '{kw}': {e}")
            await asyncio.sleep(1)
    return results


def dedup_hash(company: str, title: str, location: str) -> str:
    key = f"{company}|{title}|{location}".lower().strip()
    return hashlib.sha256(key.encode()).hexdigest()


async def scrape_jds(keywords: list[str]) -> list[dict[str, Any]]:
    """
    Fetch JDs from all sources, deduplicate on (company+title+location),
    and validate minimum text length.
    """
    raw: list[dict[str, Any]] = []
    raw.extend(await _fetch_remoteok(keywords))
    raw.extend(await _fetch_adzuna(keywords))

    seen: set[str] = set()
    valid: list[dict[str, Any]] = []
    for job in raw:
        h = dedup_hash(job["company"], job["title"], job.get("location", ""))
        if h in seen:
            continue
        seen.add(h)
        if len(job.get("raw_text", "")) < 100:
            continue
        job["dedup_hash"] = h
        valid.append(job)

    # Rank by keyword relevance so the small candidate cap keeps the JDs most
    # likely to matter (RemoteOK tag feeds include loosely-tagged noise).
    kw_tokens = {t for kw in keywords for t in _tokens(kw)}

    def _relevance(job: dict[str, Any]) -> int:
        hay = (job.get("title", "") + " " + job.get("raw_text", "")[:600]).lower()
        return sum(1 for t in kw_tokens if t and t in hay)

    valid.sort(key=_relevance, reverse=True)
    capped = valid[:MAX_CANDIDATES]

    print(f"[scraper] {len(raw)} raw → {len(valid)} valid → {len(capped)} kept (cap {MAX_CANDIDATES})")
    return capped
