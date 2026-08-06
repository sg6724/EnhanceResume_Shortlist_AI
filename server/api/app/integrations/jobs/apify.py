from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import quote
from urllib.parse import urlparse

import httpx

from ...config import settings


APIFY_BASE = "https://api.apify.com/v2"


@dataclass(frozen=True)
class SourceRequest:
    source: str
    actor_id: str
    urls: list[str]


def split_urls(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = re.split(r"[\n,]+", value)
    else:
        parts = list(value)
    seen: set[str] = set()
    urls: list[str] = []
    for raw in parts:
        url = str(raw).strip()
        if not url or url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def build_source_requests(
    *,
    career_urls: Iterable[str] | None = None,
    linkedin_urls: Iterable[str] | None = None,
    x_urls: Iterable[str] | None = None,
) -> list[SourceRequest]:
    configured = settings.apify
    return [
        SourceRequest(
            source="career_page",
            actor_id=configured.career_actor_id,
            urls=split_urls(career_urls) or split_urls(configured.career_urls),
        ),
        SourceRequest(
            source="linkedin",
            actor_id=configured.linkedin_actor_id,
            urls=split_urls(linkedin_urls) or split_urls(configured.linkedin_urls),
        ),
        SourceRequest(
            source="x",
            actor_id=configured.x_actor_id,
            urls=split_urls(x_urls) or split_urls(configured.x_urls),
        ),
    ]


def _first_text(item: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, list):
            text = "\n".join(str(v).strip() for v in value if str(v).strip())
            if text:
                return text
    return ""


def _hostname(value: str) -> str:
    host = urlparse(value).netloc.lower()
    return host.removeprefix("www.").split(":")[0]


def _extract_url(item: dict[str, Any], fallback: str = "") -> str:
    return _first_text(
        item,
        (
            "url",
            "jobUrl",
            "job_url",
            "postingUrl",
            "applyUrl",
            "apply_url",
            "link",
            "permalink",
            "tweetUrl",
            "postUrl",
        ),
    ) or fallback


def _normalize_item(item: dict[str, Any], source: str, fallback_url: str = "") -> dict[str, Any] | None:
    title = _first_text(item, ("title", "jobTitle", "job_title", "position", "role", "headline", "pageTitle"))
    company = _first_text(item, ("company", "companyName", "company_name", "organization", "authorName", "profileName"))
    location = _first_text(item, ("location", "jobLocation", "job_location", "city", "workplaceType"))
    url = _extract_url(item, fallback_url)
    body = _first_text(
        item,
        (
            "description",
            "jobDescription",
            "job_description",
            "text",
            "markdown",
            "content",
            "cleanedText",
            "fullText",
            "body",
            "snippet",
        ),
    )

    if not body:
        fragments = []
        for value in item.values():
            if isinstance(value, str) and len(value.strip()) > 40:
                fragments.append(value.strip())
        body = "\n".join(fragments)

    if not company and url:
        company = _hostname(url).replace(".jobs", "").replace(".com", "").title()
    raw_text = f"{title} at {company}\nLocation: {location}\nSource: {url}\n\n{body}".strip()
    if len(raw_text) < 100:
        return None

    external_id = _first_text(item, ("id", "jobId", "job_id", "urn", "tweetId", "postId")) or url
    content_hash = hashlib.sha256(raw_text.lower().encode()).hexdigest()
    return {
        "source": source,
        "company": company or "Unknown",
        "title": title or "Untitled role",
        "location": location,
        "url": url,
        "raw_text": raw_text,
        "external_id": external_id,
        "content_hash": content_hash,
    }


def _actor_input(source: str, urls: list[str], keywords: list[str]) -> dict[str, Any]:
    # Common Apify actors accept one of these URL/search fields. Extra fields are
    # ignored by many actors; actor-specific inputs can be tightened later once
    # the exact actors are chosen.
    search = " OR ".join(k for k in keywords if k)[:500]
    payload = {
        "startUrls": [{"url": url} for url in urls],
        "urls": urls,
        "proxyConfiguration": {"useApifyProxy": True},
        "maxItems": 50,
        "maxResults": 50,
        "maxCrawlPages": 50,
        "maxCrawlDepth": 2,
        "useSitemaps": False,
        "saveMarkdown": True,
        "saveHtml": False,
        "search": search,
        "query": search,
        "source": source,
    }
    if source == "career_page":
        payload["includeUrlGlobs"] = [
            {"glob": f"{url.rstrip('/')}/**"} for url in urls
        ]
    return payload


async def _run_actor(http: httpx.AsyncClient, request: SourceRequest, keywords: list[str]) -> list[dict[str, Any]]:
    if not settings.apify.api_token or not request.actor_id or not request.urls:
        return []

    actor_id = quote(request.actor_id.replace("/", "~"), safe="")
    run_url = f"{APIFY_BASE}/acts/{actor_id}/run-sync-get-dataset-items"
    resp = await http.post(
        run_url,
        params={"token": settings.apify.api_token, "clean": "true"},
        json=_actor_input(request.source, request.urls, keywords),
        timeout=180.0,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"actor HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    if isinstance(data, dict):
        items = data.get("items") or data.get("data") or []
    else:
        items = data

    normalized: list[dict[str, Any]] = []
    for item in items if isinstance(items, list) else []:
        if isinstance(item, dict):
            job = _normalize_item(item, request.source, request.urls[0] if request.urls else "")
            if job:
                normalized.append(job)
    return normalized


async def fetch_apify_jobs(
    http: httpx.AsyncClient,
    keywords: list[str],
    *,
    career_urls: Iterable[str] | None = None,
    linkedin_urls: Iterable[str] | None = None,
    x_urls: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for request in build_source_requests(
        career_urls=career_urls,
        linkedin_urls=linkedin_urls,
        x_urls=x_urls,
    ):
        try:
            results.extend(await _run_actor(http, request, keywords))
        except Exception as e:
            print(f"[apify] {request.source} actor failed: {type(e).__name__}: {e}")
    return results
