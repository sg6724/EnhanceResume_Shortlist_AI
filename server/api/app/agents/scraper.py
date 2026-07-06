from __future__ import annotations

import asyncio
import hashlib
from typing import Any

import aiohttp

from ..config import settings


async def _fetch_remoteok(keywords: list[str]) -> list[dict[str, Any]]:
    """RemoteOK public API — completely free, no auth required."""
    results: list[dict[str, Any]] = []
    async with aiohttp.ClientSession() as session:
        for kw in keywords[:4]:
            url = f"https://remoteok.com/api?tag={kw.replace(' ', '-').lower()}"
            try:
                async with session.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 JobHuntBot/1.0"},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        # First element is a legal notice dict, skip it
                        for job in (data[1:] if isinstance(data, list) else []):
                            if not isinstance(job, dict):
                                continue
                            desc = job.get("description") or job.get("tags") or ""
                            if not desc:
                                continue
                            results.append({
                                "source": "remoteok",
                                "company": job.get("company", "Unknown"),
                                "title": job.get("position", kw),
                                "location": "Remote",
                                "url": job.get("url", ""),
                                "raw_text": (
                                    f"{job.get('position', '')} at {job.get('company', '')}\n\n"
                                    f"Tags: {', '.join(job.get('tags', []))}\n\n"
                                    f"{desc}"
                                ),
                            })
            except Exception as e:
                print(f"[scraper] RemoteOK error for '{kw}': {e}")
            await asyncio.sleep(2)  # respect rate limits
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


def _dedup_hash(company: str, title: str, location: str) -> str:
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
        h = _dedup_hash(job["company"], job["title"], job.get("location", ""))
        if h in seen:
            continue
        seen.add(h)
        if len(job.get("raw_text", "")) < 100:
            continue
        job["dedup_hash"] = h
        valid.append(job)

    print(f"[scraper] {len(raw)} raw → {len(valid)} valid after dedup+validation")
    return valid
