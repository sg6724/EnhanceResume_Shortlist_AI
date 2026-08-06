from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..config import settings

router = APIRouter(prefix="/matches", tags=["matches"])


async def _get_user_id(sb, email: str) -> str:
    res = await sb.table("users").select("id").eq("email", email).maybe_single().execute()
    if not res.data:
        raise HTTPException(404, "user not found")
    return res.data["id"]


@router.get("")
async def list_matches(request: Request, limit: int = 200, offset: int = 0):
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    res = await (
        sb.table("jd_matches")
        .select("*, scraped_jds(company, title, location, url, source)")
        .eq("user_id", uid)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return res.data


@router.get("/{match_id}")
async def get_match(match_id: str, request: Request):
    sb = request.app.state.supabase
    res = await sb.table("jd_matches").select("*, scraped_jds(*)").eq("id", match_id).maybe_single().execute()
    if not res.data:
        raise HTTPException(404, "match not found")
    return res.data
