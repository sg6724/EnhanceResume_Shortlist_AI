from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..config import settings
from ..latex_utils import tex_to_plaintext

router = APIRouter(prefix="/master-resume", tags=["master-resume"])


class MasterResumeIn(BaseModel):
    tex_content: str


@router.post("")
async def upload_master(body: MasterResumeIn, request: Request):
    if not body.tex_content.strip():
        raise HTTPException(status_code=422, detail="tex_content is empty")

    plain_text = tex_to_plaintext(body.tex_content)
    sb = request.app.state.supabase

    user_res = await sb.table("users").select("id").eq("email", settings.user_email).maybe_single().execute()
    if user_res.data is None:
        raise HTTPException(status_code=404, detail="user not found; run the seed migration")
    user_id = user_res.data["id"]

    ver_res = await sb.table("master_resume").select("version").eq("user_id", user_id).order("version", desc=True).limit(1).execute()
    next_version = (ver_res.data[0]["version"] + 1) if ver_res.data else 1

    ins_res = await sb.table("master_resume").insert({
        "user_id": user_id,
        "tex_content": body.tex_content,
        "plain_text_cache": plain_text,
        "version": next_version,
    }).execute()
    inserted = ins_res.data[0]

    return {
        "id": inserted["id"],
        "version": inserted["version"],
        "created_at": inserted["created_at"],
        "plain_text_chars": len(plain_text),
    }
