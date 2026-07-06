from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks

from ..config import settings

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def _get_user_id(sb, email: str) -> str:
    res = await sb.table("users").select("id").eq("email", email).maybe_single().execute()
    if not res.data:
        raise HTTPException(404, "user not found")
    return res.data["id"]


@router.post("/scrape")
async def trigger_scrape(request: Request):
    """Enqueue a full scraping + matching batch job."""
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL not set — Procrastinate queue unavailable")
    from ..queue import scrape_and_process_task
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    await scrape_and_process_task.defer_async(user_id=uid)
    return {"queued": True, "user_id": uid}


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


@router.get("")
async def list_jds(request: Request, limit: int = 50, offset: int = 0):
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    res = await (
        sb.table("scraped_jds").select("*").eq("user_id", uid)
        .order("scraped_at", desc=True).range(offset, offset + limit - 1).execute()
    )
    return res.data
