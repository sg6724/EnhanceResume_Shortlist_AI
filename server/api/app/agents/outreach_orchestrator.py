from __future__ import annotations

from datetime import datetime, timezone

import httpx
from supabase import AsyncClient

from .letter_writer import write_application_cover_letter

MAX_DRAFT_ATTEMPTS = 3


async def _log(sb: AsyncClient, jd_id: str | None, agent: str, log: str, reasoning: str = "") -> None:
    await sb.table("agent_traces").insert({
        "jd_id": jd_id,
        "agent_name": agent,
        "log": log[:2000],
        "reasoning": reasoning[:5000],
    }).execute()


def _friendly_error(exc: Exception) -> str:
    text = str(exc).lower()
    if "429" in text or "rate limit" in text or "resource_exhausted" in text:
        return "LLM quota/rate limit exhausted. Retry after the provider reset or add more capacity."
    if "no gemini_api_key" in text and "no groq_api_key" in text:
        return "No LLM provider is configured. Add Gemini or Groq credentials."
    return "Cover letter generation failed. Check the worker logs for provider details."


async def _ingest_application_targets(user_id: str, sb: AsyncClient, threshold: float) -> int:
    matches = await (
        sb.table("jd_matches")
        .select("composite_score, jd_id, scraped_jds(id, company, title)")
        .eq("user_id", user_id)
        .gte("composite_score", threshold)
        .execute()
    )
    existing = await sb.table("outreach_targets").select("jd_id").eq("user_id", user_id).execute()
    known = {t["jd_id"] for t in existing.data if t.get("jd_id")}
    created = 0
    for match in matches.data:
        jd = match.get("scraped_jds") or {}
        jd_id = jd.get("id") or match.get("jd_id")
        if not jd_id or jd_id in known:
            continue
        await sb.table("outreach_targets").insert({
            "user_id": user_id,
            "company_name": jd.get("company") or "Unknown",
            "source": "pipeline",
            "jd_id": jd_id,
            "role_title": jd.get("title") or "",
            "status": "pending",
        }).execute()
        known.add(jd_id)
        created += 1
    return created


async def run_outreach_cycle(user_id: str, sb: AsyncClient, http: httpx.AsyncClient) -> dict:
    """Prepare cover-letter drafts for matched jobs. No contact lookup or email sending."""
    user_res = await sb.table("users").select("*").eq("id", user_id).maybe_single().execute()
    if not user_res.data:
        return {"error": "user not found"}
    user = user_res.data

    ingested = await _ingest_application_targets(user_id, sb, user["match_threshold"])

    mr_res = await (
        sb.table("master_resume")
        .select("plain_text_cache")
        .eq("user_id", user_id)
        .order("version", desc=True)
        .limit(1)
        .execute()
    )
    resume_text = mr_res.data[0]["plain_text_cache"] if mr_res.data else ""

    pending = await (
        sb.table("outreach_targets")
        .select("*")
        .eq("user_id", user_id)
        .in_("status", ["pending"])
        .lt("attempts", MAX_DRAFT_ATTEMPTS)
        .order("created_at")
        .limit(user.get("outreach_batch_size", 3))
        .execute()
    )

    drafted = failed = 0
    for target in pending.data:
        tid = target["id"]
        try:
            await sb.table("outreach_targets").update({
                "attempts": target.get("attempts", 0) + 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", tid).execute()

            jd_text = ""
            resume_copy_id = None
            if target.get("jd_id"):
                jd_res = await (
                    sb.table("scraped_jds")
                    .select("raw_text, title, company")
                    .eq("id", target["jd_id"])
                    .maybe_single()
                    .execute()
                )
                if jd_res and jd_res.data:
                    jd_text = jd_res.data.get("raw_text") or ""
                    target["role_title"] = target.get("role_title") or jd_res.data.get("title")
                    target["company_name"] = target.get("company_name") or jd_res.data.get("company")
                copy_res = await (
                    sb.table("resume_copies")
                    .select("id")
                    .eq("jd_id", target["jd_id"])
                    .eq("status", "compiled")
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if copy_res.data:
                    resume_copy_id = copy_res.data[0]["id"]

            role = target.get("role_title") or "the open role"
            subject, body = await write_application_cover_letter(
                resume_text=resume_text,
                jd_text=jd_text,
                role_title=role,
                company_name=target.get("company_name") or "the company",
            )
            await sb.table("outreach_drafts").insert({
                "target_id": tid,
                "subject": subject,
                "body": body,
                "resume_copy_id": resume_copy_id,
            }).execute()
            await sb.table("outreach_targets").update({"status": "drafted"}).eq("id", tid).execute()
            await _log(sb, target.get("jd_id"), "cover_letter", f"drafted for {target.get('company_name')}: {subject}")
            drafted += 1
        except Exception as e:
            friendly = _friendly_error(e)
            failed += 1
            await sb.table("outreach_targets").update({
                "status": "failed",
                "failure_reason": friendly,
            }).eq("id", tid).execute()
            await _log(sb, target.get("jd_id"), "application_prep", f"draft failed: {friendly}", str(e)[:5000])

    await sb.table("users").update(
        {"outreach_last_run_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", user_id).execute()

    return {"ingested": ingested, "processed": len(pending.data), "drafted": drafted, "failed": failed}


async def send_outreach(draft_id: str, sb: AsyncClient, http: httpx.AsyncClient) -> dict:
    """Legacy task retained for queued old jobs; direct sending is disabled."""
    draft_res = await sb.table("outreach_drafts").select("target_id").eq("id", draft_id).maybe_single().execute()
    if draft_res and draft_res.data:
        await sb.table("outreach_targets").update({"status": "drafted"}).eq("id", draft_res.data["target_id"]).execute()
    return {"error": "direct email sending is disabled; review the cover letter and apply manually"}
