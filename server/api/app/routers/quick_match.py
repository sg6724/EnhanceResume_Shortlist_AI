from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..config import settings
from ..agents.jd_fetch import fetch_jd_from_url
from ..agents.scraper import dedup_hash

router = APIRouter(prefix="/quick-match", tags=["quick-match"])


class FetchUrlIn(BaseModel):
    url: str


class SubmitIn(BaseModel):
    jd_text: str
    company: str
    title: str


async def _get_user_id(sb, email: str) -> str:
    res = await sb.table("users").select("id").eq("email", email).maybe_single().execute()
    if not res.data:
        raise HTTPException(404, "user not found")
    return res.data["id"]


@router.post("/fetch-url")
async def fetch_url(body: FetchUrlIn, request: Request):
    if not body.url.strip():
        raise HTTPException(422, "url is required")
    result = await fetch_jd_from_url(request.app.state.http, body.url.strip())
    if "error" in result:
        raise HTTPException(422, result["error"])
    return result


@router.post("")
async def submit(body: SubmitIn, request: Request):
    if not body.jd_text.strip():
        raise HTTPException(422, "jd_text is required")
    if not body.company.strip() or not body.title.strip():
        raise HTTPException(422, "company and title are required")
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL not set — Procrastinate queue unavailable")

    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)

    mr_res = await (
        sb.table("master_resume").select("id").eq("user_id", uid)
        .order("version", desc=True).limit(1).execute()
    )
    if not mr_res.data:
        raise HTTPException(404, "no master resume uploaded — upload one on the Master Resume page first")

    company = body.company.strip()
    title = body.title.strip()
    jd_ins = await sb.table("scraped_jds").upsert({
        "user_id": uid,
        "source": "manual",
        "company": company,
        "title": title,
        "location": "",
        "url": "",
        "raw_text": body.jd_text.strip(),
        "relevance_confirmed": True,
        "dedup_hash": dedup_hash(company, title, ""),
    }, on_conflict="dedup_hash").execute()
    jd_id = jd_ins.data[0]["id"]

    from ..queue import run_manual_match_task
    await run_manual_match_task.defer_async(jd_id=jd_id)
    return {"jd_id": jd_id, "queued": True}


@router.get("/{jd_id}")
async def status(jd_id: str, request: Request):
    sb = request.app.state.supabase
    jd_res = await sb.table("scraped_jds").select("id").eq("id", jd_id).maybe_single().execute()
    if not jd_res.data:
        raise HTTPException(404, "job not found")

    match_res = await (
        sb.table("jd_matches").select("*").eq("jd_id", jd_id)
        .order("created_at", desc=True).limit(1).execute()
    )
    copy_res = await (
        sb.table("resume_copies").select("*, scraped_jds(company, title)").eq("jd_id", jd_id)
        .order("created_at", desc=True).limit(1).execute()
    )
    return {
        "match": match_res.data[0] if match_res.data else None,
        "copy": copy_res.data[0] if copy_res.data else None,
    }
