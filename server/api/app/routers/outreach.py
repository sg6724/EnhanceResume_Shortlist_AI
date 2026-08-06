from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..config import settings

router = APIRouter(prefix="/outreach", tags=["application-prep"])


class WatchlistIn(BaseModel):
    company_name: str
    company_domain: str | None = None


class TargetPatch(BaseModel):
    founder_name: str | None = None
    founder_title: str | None = None
    founder_email: str | None = None
    retry: bool = False


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


@router.post("/watchlist", status_code=201)
async def add_watchlist(body: WatchlistIn, request: Request):
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    company = body.company_name.strip()
    if not company:
        raise HTTPException(422, "company_name is required")
    dup = await (
        sb.table("outreach_targets")
        .select("id")
        .eq("user_id", uid)
        .eq("company_name", company)
        .is_("jd_id", "null")
        .maybe_single()
        .execute()
    )
    if dup and dup.data:
        raise HTTPException(409, "company already tracked")
    res = await sb.table("outreach_targets").insert({
        "user_id": uid,
        "company_name": company,
        "company_domain": body.company_domain,
        "source": "watchlist",
        "status": "pending",
    }).execute()
    return res.data[0]


@router.patch("/targets/{target_id}")
async def patch_target(target_id: str, body: TargetPatch, request: Request):
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    cur = await (
        sb.table("outreach_targets")
        .select("*")
        .eq("id", target_id)
        .eq("user_id", uid)
        .maybe_single()
        .execute()
    )
    if not cur or not cur.data:
        raise HTTPException(404, "target not found")
    updates: dict = {}
    if body.retry:
        updates = {"status": "pending", "failure_reason": None, "attempts": 0}
    if body.founder_name is not None:
        updates["founder_name"] = body.founder_name
    if body.founder_title is not None:
        updates["founder_title"] = body.founder_title
    if body.founder_email is not None:
        updates["founder_email"] = body.founder_email
    if not updates:
        raise HTTPException(400, "nothing to update")
    res = await sb.table("outreach_targets").update(updates).eq("id", target_id).execute()
    return res.data[0]


@router.delete("/targets/{target_id}")
async def delete_target(target_id: str, request: Request):
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    await sb.table("outreach_targets").delete().eq("id", target_id).eq("user_id", uid).execute()
    return {"deleted": target_id}


@router.get("/drafts")
async def list_drafts(request: Request):
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    res = await (
        sb.table("outreach_drafts")
        .select("*, outreach_targets!inner(*)")
        .eq("outreach_targets.user_id", uid)
        .in_("outreach_targets.status", ["drafted", "approved"])
        .is_("sent_at", "null")
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


@router.post("/run")
async def run_now(request: Request):
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL not set; Procrastinate queue unavailable")
    sb = request.app.state.supabase
    uid = await _get_user_id(sb, settings.user_email)
    from ..queue import run_outreach_task
    await run_outreach_task.defer_async(user_id=uid)
    return {"queued": True}


@router.get("/quota")
async def quota(request: Request):
    return {
        "apify_configured": bool(settings.apify.api_token),
        "career_actor_configured": bool(settings.apify.career_actor_id),
        "linkedin_actor_configured": bool(settings.apify.linkedin_actor_id),
        "x_actor_configured": bool(settings.apify.x_actor_id),
    }
