from __future__ import annotations

from datetime import datetime, timezone

import httpx
from supabase import AsyncClient

from ..latex_utils import tex_to_plaintext
from ..services.pdf_storage import store_pdf
from .compiler import compile_with_retry
from .jd_fetch import extract_jd_structured
from .letter_writer import write_application_cover_letter
from .matcher import compute_match
from .rewriter import rewrite_resume
from .scraper import scrape_jds


async def _log(sb: AsyncClient, jd_id: str | None, agent: str, log: str, reasoning: str = "") -> None:
    await sb.table("agent_traces").insert({
        "jd_id": jd_id, "agent_name": agent, "log": log[:2000], "reasoning": reasoning[:5000],
    }).execute()


async def tailor_and_draft(
    *,
    jd: dict,
    master: dict,
    user: dict,
    sb: AsyncClient,
    http: httpx.AsyncClient,
    match_data: dict,
    origin: str,
) -> dict:
    """Fork+rewrite+compile a tailored resume for `jd`, draft a cover letter from
    the TAILORED resume's text (falls back to the master resume's plain text only
    if compile failed), and persist one outreach_targets + outreach_drafts row.
    Always runs regardless of match_data['composite_score'] — the caller already
    decided this JD is worth a letter. Never raises past this boundary; a letter
    failure lands as a 'failed' outreach_targets row, not an exception.
    """
    user_id = jd["user_id"]
    jd_id = jd["id"]

    copy_ins = await sb.table("resume_copies").insert({
        "jd_id": jd_id, "user_id": user_id, "master_resume_id": master["id"],
        "status": "compiling", "tex_content": master["tex_content"],
    }).execute()
    copy_id = copy_ins.data[0]["id"]

    try:
        rewritten_tex, diff_summary = await rewrite_resume(
            master_tex=master["tex_content"], jd_text=jd["raw_text"],
            gap_analysis=match_data.get("gap_analysis", ""), position_context=jd["title"],
        )
    except ValueError as e:
        await _log(sb, jd_id, "rewriter", f"Structure violation: {e}")
        rewritten_tex, diff_summary = master["tex_content"], f"Rewrite failed (structure violation): {e}"

    async def rewriter_fn(current_tex: str, error_log: str, attempt: int) -> tuple[str, str]:
        return await rewrite_resume(
            master_tex=current_tex, jd_text=jd["raw_text"],
            gap_analysis=match_data.get("gap_analysis", ""), position_context=jd["title"],
            attempt=attempt, previous_error=error_log,
        )

    pdf_bytes, final_tex, error_log = await compile_with_retry(
        http=http, tex=rewritten_tex, rewriter_fn=rewriter_fn,
        max_retries=user.get("max_compiler_retries", 3),
        jd_info={"company": jd.get("company"), "title": jd.get("title")},
    )

    copy_status = "compiled" if pdf_bytes else "failed"
    updates: dict = {"tex_content": final_tex, "diff_patch": diff_summary, "status": copy_status}
    if pdf_bytes:
        try:
            updates["pdf_storage_path"] = await store_pdf(sb, user_id, copy_id, pdf_bytes)
        except Exception as e:
            await _log(sb, jd_id, "compiler", f"PDF storage upload failed (non-fatal): {e}")
    await sb.table("resume_copies").update(updates).eq("id", copy_id).execute()

    if pdf_bytes:
        await _log(sb, jd_id, "compiler", f"PDF compiled successfully ({len(pdf_bytes):,} bytes)")
    else:
        await _log(sb, jd_id, "compiler", "FAILED after all retries", error_log[:1000])

    tailored_text = tex_to_plaintext(final_tex) if pdf_bytes else master["plain_text_cache"]

    target_ins = await sb.table("outreach_targets").insert({
        "user_id": user_id, "company_name": jd.get("company") or "Unknown",
        "source": origin, "jd_id": jd_id, "role_title": jd.get("title") or "",
        "status": "drafted",
    }).execute()
    target_id = target_ins.data[0]["id"]

    try:
        subject, body = await write_application_cover_letter(
            resume_text=tailored_text, jd_text=jd["raw_text"],
            role_title=jd.get("title") or "the open role",
            company_name=jd.get("company") or "the company",
        )
    except Exception as e:
        await sb.table("outreach_targets").update({
            "status": "failed",
            "failure_reason": "Cover letter generation failed. Check the worker logs for provider details.",
        }).eq("id", target_id).execute()
        await _log(sb, jd_id, "cover_letter", f"draft failed: {e}", str(e)[:5000])
        return {"copy_id": copy_id, "target_id": target_id, "draft_id": None, "status": "failed"}

    draft_ins = await sb.table("outreach_drafts").insert({
        "target_id": target_id, "subject": subject, "body": body,
        "resume_copy_id": copy_id if pdf_bytes else None,
    }).execute()
    draft_id = draft_ins.data[0]["id"]
    await _log(sb, jd_id, "cover_letter", f"drafted for {jd.get('company')}: {subject}")

    return {"copy_id": copy_id, "target_id": target_id, "draft_id": draft_id, "status": "drafted"}


async def _touch_run(sb: AsyncClient, run_id: str, values: dict) -> None:
    await sb.table("application_runs").update({
        **values, "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", run_id).execute()


async def run_application_prep(
    run_id: str,
    user_id: str,
    sb: AsyncClient,
    http: httpx.AsyncClient,
    career_urls: list[str],
    linkedin_urls: list[str],
    x_urls: list[str],
) -> dict:
    """Scrape exactly the given URLs, score + tailor + draft a letter for every
    JD found that isn't already an outreach target, and track progress on the
    application_runs row so the frontend can show a real percentage."""
    user_res = await sb.table("users").select("*").eq("id", user_id).maybe_single().execute()
    if not user_res.data:
        await _touch_run(sb, run_id, {"status": "failed", "error": "user not found"})
        return {"error": "user not found"}
    user = user_res.data

    mr_res = await (
        sb.table("master_resume").select("*").eq("user_id", user_id)
        .order("version", desc=True).limit(1).execute()
    )
    if not mr_res.data:
        await _touch_run(sb, run_id, {"status": "failed", "error": "no master resume uploaded"})
        return {"error": "no master resume uploaded"}
    master = mr_res.data[0]

    raw_jds = await scrape_jds(
        [], http=http, career_urls=career_urls, linkedin_urls=linkedin_urls, x_urls=x_urls,
    )
    await _touch_run(sb, run_id, {"jds_found": len(raw_jds)})

    existing = await sb.table("outreach_targets").select("jd_id").eq("user_id", user_id).execute()
    known_jd_ids = {t["jd_id"] for t in existing.data if t.get("jd_id")}

    jds_done = targets_drafted = targets_failed = 0
    for raw_jd in raw_jds:
        extracted = await extract_jd_structured(raw_jd["raw_text"])
        jd_ins = await sb.table("scraped_jds").upsert({
            "user_id": user_id, "source": raw_jd["source"], "company": raw_jd["company"],
            "title": raw_jd["title"], "location": raw_jd.get("location", ""), "url": raw_jd.get("url", ""),
            "raw_text": raw_jd["raw_text"], "relevance_confirmed": True, "dedup_hash": raw_jd["dedup_hash"],
            "role_title": extracted.role_title or raw_jd["title"], "seniority": extracted.seniority,
            "responsibilities": extracted.responsibilities, "must_have_skills": extracted.must_have_skills,
            "nice_to_have_skills": extracted.nice_to_have_skills, "tech_stack": extracted.tech_stack,
        }, on_conflict="dedup_hash").execute()
        jd_row = jd_ins.data[0]
        jd_id = jd_row["id"]

        if jd_id in known_jd_ids:
            jds_done += 1
            await _touch_run(sb, run_id, {"jds_done": jds_done})
            continue
        known_jd_ids.add(jd_id)

        skill_terms = extracted.must_have_skills + extracted.nice_to_have_skills + extracted.tech_stack
        match_data = await compute_match(
            raw_jd["raw_text"], master["plain_text_cache"], jd_row["title"],
            skill_terms=skill_terms, must_have_skills=extracted.must_have_skills,
            nice_to_have_skills=extracted.nice_to_have_skills, tech_stack=extracted.tech_stack,
            seniority=extracted.seniority, location=raw_jd.get("location", ""),
        )
        await sb.table("jd_matches").insert({
            "jd_id": jd_id, "user_id": user_id, "position_context": jd_row["title"], **match_data,
        }).execute()

        result = await tailor_and_draft(
            jd=jd_row, master=master, user=user, sb=sb, http=http,
            match_data=match_data, origin=jd_row["source"],
        )
        jds_done += 1
        if result["status"] == "drafted":
            targets_drafted += 1
        else:
            targets_failed += 1
        await _touch_run(sb, run_id, {
            "jds_done": jds_done, "targets_drafted": targets_drafted, "targets_failed": targets_failed,
        })

    await _touch_run(sb, run_id, {"status": "done"})
    return {
        "jds_found": len(raw_jds), "jds_done": jds_done,
        "targets_drafted": targets_drafted, "targets_failed": targets_failed,
    }


async def retry_target(target_id: str, sb: AsyncClient, http: httpx.AsyncClient) -> dict:
    """Delete the failed target (cascades to its draft, if any) and re-run the
    full tailor+draft step fresh for the same JD."""
    target_res = await sb.table("outreach_targets").select("*").eq("id", target_id).maybe_single().execute()
    if not target_res.data:
        return {"error": "target not found"}
    target = target_res.data
    jd_id = target.get("jd_id")
    if not jd_id:
        return {"error": "target has no linked job description"}

    jd_res = await sb.table("scraped_jds").select("*").eq("id", jd_id).maybe_single().execute()
    if not jd_res.data:
        return {"error": "job description not found"}
    jd = jd_res.data
    user_id = target["user_id"]

    user_res = await sb.table("users").select("*").eq("id", user_id).maybe_single().execute()
    if not user_res.data:
        return {"error": "user not found"}
    user = user_res.data

    mr_res = await (
        sb.table("master_resume").select("*").eq("user_id", user_id)
        .order("version", desc=True).limit(1).execute()
    )
    if not mr_res.data:
        return {"error": "no master resume"}
    master = mr_res.data[0]

    match_res = await (
        sb.table("jd_matches").select("*").eq("jd_id", jd_id).eq("user_id", user_id)
        .order("composite_score", desc=True).limit(1).execute()
    )
    match_data = match_res.data[0] if match_res.data else {}

    attempts = target.get("attempts", 0) + 1
    origin = target.get("source", "career_page")
    await sb.table("outreach_targets").delete().eq("id", target_id).execute()

    result = await tailor_and_draft(
        jd=jd, master=master, user=user, sb=sb, http=http, match_data=match_data, origin=origin,
    )
    await sb.table("outreach_targets").update({"attempts": attempts}).eq("id", result["target_id"]).execute()
    return result
