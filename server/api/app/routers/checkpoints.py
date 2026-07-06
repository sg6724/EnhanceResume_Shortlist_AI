from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..config import settings

router = APIRouter(prefix="/checkpoints", tags=["checkpoints"])


async def _get_user_id(sb, email: str) -> str:
    res = await sb.table("users").select("id").eq("email", email).maybe_single().execute()
    if not res.data:
        raise HTTPException(404, "user not found")
    return res.data["id"]


@router.get("")
async def list_checkpoints(request: Request):
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    res = await (
        sb.table("checkpoint_state")
        .select("*, scraped_jds(company, title)")
        .eq("user_id", uid)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


@router.post("/{checkpoint_id}/approve")
async def approve_checkpoint(checkpoint_id: str, request: Request):
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL not set — queue unavailable")
    sb = request.app.state.supabase
    cp = await sb.table("checkpoint_state").select("*").eq("id", checkpoint_id).maybe_single().execute()
    if not cp.data:
        raise HTTPException(404, "checkpoint not found")
    await sb.table("checkpoint_state").update({"status": "approved"}).eq("id", checkpoint_id).execute()
    from ..queue import rewrite_resume_task
    await rewrite_resume_task.defer_async(checkpoint_id=checkpoint_id)
    return {"status": "approved"}


@router.post("/{checkpoint_id}/reject")
async def reject_checkpoint(checkpoint_id: str, request: Request):
    sb = request.app.state.supabase
    await sb.table("checkpoint_state").update({"status": "rejected"}).eq("id", checkpoint_id).execute()
    return {"status": "rejected"}
