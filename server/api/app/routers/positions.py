from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..config import settings

router = APIRouter(prefix="/positions", tags=["positions"])


class PositionIn(BaseModel):
    title: str
    fuzzy_keywords: list[str] = []


async def _get_user_id(sb, email: str) -> str:
    res = await sb.table("users").select("id").eq("email", email).maybe_single().execute()
    if not res.data:
        raise HTTPException(404, "user not found; check DB seed")
    return res.data["id"]


@router.get("")
async def list_positions(request: Request):
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    res = await sb.table("target_positions").select("*").eq("user_id", uid).order("created_at", desc=True).execute()
    return res.data


@router.post("", status_code=201)
async def create_position(body: PositionIn, request: Request):
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    res = await sb.table("target_positions").insert({
        "user_id": uid,
        "title": body.title,
        "fuzzy_keywords": body.fuzzy_keywords,
    }).execute()
    return res.data[0]


@router.patch("/{pos_id}/toggle")
async def toggle_position(pos_id: str, request: Request):
    sb = request.app.state.supabase
    cur = await sb.table("target_positions").select("is_active").eq("id", pos_id).maybe_single().execute()
    if not cur.data:
        raise HTTPException(404, "position not found")
    res = await sb.table("target_positions").update(
        {"is_active": not cur.data["is_active"]}
    ).eq("id", pos_id).execute()
    return res.data[0]


@router.delete("/{pos_id}")
async def delete_position(pos_id: str, request: Request):
    sb = request.app.state.supabase
    await sb.table("target_positions").delete().eq("id", pos_id).execute()
    return {"deleted": pos_id}
