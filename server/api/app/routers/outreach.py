from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..config import settings

router = APIRouter(prefix="/outreach", tags=["application-prep"])


class PrepareIn(BaseModel):
    career_urls: list[str] = []
    linkedin_urls: list[str] = []
    x_urls: list[str] = []


class DraftPatch(BaseModel):
    subject: str | None = None
    body: str | None = None


async def _get_user_id(sb, email: str) -> str:
    res = await sb.table("users").select("id").eq("email", email).maybe_single().execute()
    if not res.data:
        raise HTTPException(404, "user not found; check DB seed")
    return res.data["id"]


@router.get("/targets")
async def list_targets(request: Request):
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    res = await (
        sb.table("outreach_targets")
        .select("*")
        .eq("user_id", uid)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


@router.delete("/targets/{target_id}")
async def delete_target(target_id: str, request: Request):
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    await sb.table("outreach_targets").delete().eq("id", target_id).eq("user_id", uid).execute()
    return {"deleted": target_id}


@router.post("/targets/{target_id}/retry")
async def retry_target(target_id: str, request: Request):
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL not set; Procrastinate queue unavailable")
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    cur = await (
        sb.table("outreach_targets").select("id").eq("id", target_id).eq("user_id", uid).maybe_single().execute()
    )
    if not cur or not cur.data:
        raise HTTPException(404, "target not found")
    from ..queue import retry_application_target_task
    await retry_application_target_task.defer_async(target_id=target_id)
    return {"queued": True}


@router.get("/drafts")
async def list_drafts(request: Request):
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    res = await (
        sb.table("outreach_drafts")
        .select("*, outreach_targets!inner(*)")
        .eq("outreach_targets.user_id", uid)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


@router.patch("/drafts/{draft_id}")
async def patch_draft(draft_id: str, body: DraftPatch, request: Request):
    sb = request.app.state.supabase
    updates: dict = {}
    if body.subject is not None:
        updates["edited_subject"] = body.subject
    if body.body is not None:
        updates["edited_body"] = body.body
    if not updates:
        raise HTTPException(400, "nothing to update")
    res = await sb.table("outreach_drafts").update(updates).eq("id", draft_id).execute()
    if not res.data:
        raise HTTPException(404, "draft not found")
    return res.data[0]


@router.post("/drafts/{draft_id}/approve")
async def approve_draft(draft_id: str, request: Request):
    sb = request.app.state.supabase
    draft = await (
        sb.table("outreach_drafts")
        .select("id, target_id, outreach_targets(status)")
        .eq("id", draft_id)
        .maybe_single()
        .execute()
    )
    if not draft or not draft.data:
        raise HTTPException(404, "draft not found")
    target = draft.data["outreach_targets"]
    if target["status"] not in ("drafted", "approved"):
        raise HTTPException(400, f"target status is '{target['status']}'")
    await sb.table("outreach_targets").update({"status": "approved"}).eq("id", draft.data["target_id"]).execute()
    return {"status": "approved"}


@router.post("/drafts/{draft_id}/reject")
async def reject_draft(draft_id: str, request: Request):
    sb = request.app.state.supabase
    draft = await sb.table("outreach_drafts").select("target_id").eq("id", draft_id).maybe_single().execute()
    if not draft or not draft.data:
        raise HTTPException(404, "draft not found")
    await sb.table("outreach_targets").update({"status": "skipped"}).eq("id", draft.data["target_id"]).execute()
    return {"status": "skipped"}


@router.post("/prepare", status_code=201)
async def prepare_application(body: PrepareIn, request: Request):
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL not set; Procrastinate queue unavailable")
    if not (body.career_urls or body.linkedin_urls or body.x_urls):
        raise HTTPException(422, "at least one URL is required")
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    run_ins = await sb.table("application_runs").insert({
        "user_id": uid, "status": "running",
        "career_urls": body.career_urls, "linkedin_urls": body.linkedin_urls, "x_urls": body.x_urls,
    }).execute()
    run_id = run_ins.data[0]["id"]
    from ..queue import prepare_application_task
    await prepare_application_task.defer_async(
        run_id=run_id, user_id=uid,
        career_urls=body.career_urls, linkedin_urls=body.linkedin_urls, x_urls=body.x_urls,
    )
    return {"run_id": run_id}


@router.get("/runs/{run_id}")
async def get_run(run_id: str, request: Request):
    sb = request.app.state.supabase
    res = await sb.table("application_runs").select("*").eq("id", run_id).maybe_single().execute()
    if not res or not res.data:
        raise HTTPException(404, "run not found")
    run = res.data
    if run["status"] != "running":
        percent = 100
    elif run["jds_found"] == 0:
        percent = 5
    else:
        percent = min(95, round(10 + 90 * run["jds_done"] / run["jds_found"]))
    return {**run, "percent": percent}
