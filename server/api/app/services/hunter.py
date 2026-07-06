from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx

from ..config import settings

HUNTER_MONTHLY_LIMIT = 25

LEADER_TITLE_RE = re.compile(
    r"\b(cto|chief technology officer|co[\s-]?founder|founder|"
    r"(head|vp) of engineering)\b",
    re.IGNORECASE,
)


def pick_leader(people: list[dict]) -> dict | None:
    """Pick the highest-confidence person whose title matches a tech-leader role."""
    leaders = [p for p in people if p.get("position") and LEADER_TITLE_RE.search(p["position"])]
    if not leaders:
        return None
    return max(leaders, key=lambda p: p.get("confidence") or 0)


async def hunter_domain_search(http: httpx.AsyncClient, domain: str) -> list[dict]:
    """Return Hunter 'emails' list for a domain; [] when no key or on any error."""
    if not settings.hunter_api_key:
        return []
    try:
        resp = await http.get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": domain, "api_key": settings.hunter_api_key, "limit": 10},
        )
        if resp.status_code != 200:
            print(f"[hunter] {domain} -> HTTP {resp.status_code}")
            return []
        return resp.json().get("data", {}).get("emails", []) or []
    except Exception as e:
        print(f"[hunter] error for {domain}: {e}")
        return []


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


async def hunter_quota_remaining(sb) -> int:
    try:
        res = await (
            sb.table("api_quota_usage").select("count")
            .eq("provider", "hunter").eq("month", _month_key())
            .maybe_single().execute()
        )
    except Exception as e:
        print(f"[hunter] quota check error: {e}")
        return 0
    used = res.data["count"] if res and res.data else 0
    return max(0, HUNTER_MONTHLY_LIMIT - used)


async def increment_hunter_quota(sb) -> None:
    month = _month_key()
    try:
        await sb.rpc("increment_api_quota", {"p_provider": "hunter", "p_month": month}).execute()
    except Exception as e:
        print(f"[hunter] quota increment error: {e}")
