from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..config import settings

router = APIRouter(prefix="/jobs", tags=["jobs"])


class ScrapeIn(BaseModel):
    career_urls: list[str] = []
    linkedin_urls: list[str] = []
    x_urls: list[str] = []


async def _get_user_id(sb, email: str) -> str:
    res = await sb.table("users").select("id").eq("email", email).maybe_single().execute()
    if not res.data:
        raise HTTPException(404, "user not found")
    return res.data["id"]


@router.post("/scrape")
async def trigger_scrape(request: Request, body: ScrapeIn | None = None):
    """Enqueue a full scraping + matching batch job."""
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL not set — Procrastinate queue unavailable")
    from ..queue import scrape_and_process_task
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    payload = body or ScrapeIn()
    await scrape_and_process_task.defer_async(
        user_id=uid,
        career_urls=payload.career_urls,
        linkedin_urls=payload.linkedin_urls,
        x_urls=payload.x_urls,
    )
    return {
        "queued": True,
        "user_id": uid,
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "career_urls": len(payload.career_urls),
            "linkedin_urls": len(payload.linkedin_urls),
            "x_urls": len(payload.x_urls),
        },
    }


@router.get("/stats")
async def stats(request: Request):
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    jds = await sb.table("scraped_jds").select("id", count="exact").eq("user_id", uid).execute()
    matches = await sb.table("jd_matches").select("id", count="exact").eq("user_id", uid).execute()
    copies = await sb.table("resume_copies").select("id", count="exact").eq("user_id", uid).execute()
    chk = await (
        sb.table("checkpoint_state").select("id", count="exact")
        .eq("user_id", uid).eq("status", "pending").execute()
    )
    return {
        "total_jds": jds.count or 0,
        "total_matches": matches.count or 0,
        "total_copies": copies.count or 0,
        "pending_checkpoints": chk.count or 0,
    }


@router.get("/activity")
async def activity(request: Request):
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    stats_payload = await stats(request)
    recent_jds = await (
        sb.table("scraped_jds")
        .select("id, source, company, title, location, url, scraped_at")
        .eq("user_id", uid)
        .order("scraped_at", desc=True)
        .limit(8)
        .execute()
    )
    recent_matches = await (
        sb.table("jd_matches")
        .select("id, composite_score, position_context, created_at, scraped_jds(company, title, source)")
        .eq("user_id", uid)
        .order("created_at", desc=True)
        .limit(8)
        .execute()
    )
    targets = await (
        sb.table("outreach_targets")
        .select("id, company_name, role_title, status, created_at, updated_at")
        .eq("user_id", uid)
        .order("created_at", desc=True)
        .limit(8)
        .execute()
    )
    drafts = await (
        sb.table("outreach_drafts")
        .select("id, subject, created_at, outreach_targets!inner(user_id, company_name, role_title, status)")
        .eq("outreach_targets.user_id", uid)
        .order("created_at", desc=True)
        .limit(8)
        .execute()
    )
    traces = await (
        sb.table("agent_traces")
        .select("id, jd_id, agent_name, log, created_at")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    return {
        "stats": stats_payload,
        "recent_jds": recent_jds.data,
        "recent_matches": recent_matches.data,
        "targets": targets.data,
        "drafts": drafts.data,
        "traces": traces.data,
    }


@router.get("")
async def list_jds(request: Request, limit: int = 50, offset: int = 0):
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    res = await (
        sb.table("scraped_jds").select("*").eq("user_id", uid)
        .order("scraped_at", desc=True).range(offset, offset + limit - 1).execute()
    )
    return res.data
