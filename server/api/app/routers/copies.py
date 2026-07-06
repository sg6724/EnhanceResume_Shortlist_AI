from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..config import settings
from ..compile_client import compile_tex

router = APIRouter(prefix="/copies", tags=["copies"])


class TexUpdateIn(BaseModel):
    tex_content: str


async def _get_user_id(sb, email: str) -> str:
    res = await sb.table("users").select("id").eq("email", email).maybe_single().execute()
    if not res.data:
        raise HTTPException(404, "user not found")
    return res.data["id"]


@router.get("")
async def list_copies(request: Request, limit: int = 50, offset: int = 0):
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    res = await (
        sb.table("resume_copies")
        .select("*, scraped_jds(company, title)")
        .eq("user_id", uid)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return res.data


@router.get("/{copy_id}")
async def get_copy(copy_id: str, request: Request):
    sb = request.app.state.supabase
    res = await sb.table("resume_copies").select("*, scraped_jds(*)").eq("id", copy_id).maybe_single().execute()
    if not res.data:
        raise HTTPException(404, "copy not found")
    return res.data


@router.patch("/{copy_id}/tex")
async def update_tex(copy_id: str, body: TexUpdateIn, request: Request):
    """Manual edit — recompile only, no agent re-run."""
    sb = request.app.state.supabase
    await sb.table("resume_copies").update(
        {"tex_content": body.tex_content, "status": "compiling"}
    ).eq("id", copy_id).execute()

    resp = await compile_tex(request.app.state.http, body.tex_content)
    if resp.status_code == 200:
        await sb.table("resume_copies").update({"status": "compiled"}).eq("id", copy_id).execute()
        return {"status": "compiled"}
    await sb.table("resume_copies").update({"status": "failed"}).eq("id", copy_id).execute()
    return {"status": "failed", "log": resp.json().get("log", "")[:500]}


@router.patch("/{copy_id}/apply")
async def mark_applied(copy_id: str, request: Request):
    sb = request.app.state.supabase
    res = await sb.table("resume_copies").update({"is_applied": True}).eq("id", copy_id).execute()
    if not res.data:
        raise HTTPException(404, "copy not found")
    return res.data[0]
