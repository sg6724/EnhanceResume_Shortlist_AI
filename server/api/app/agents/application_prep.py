from __future__ import annotations

import httpx
from supabase import AsyncClient

from ..latex_utils import tex_to_plaintext
from ..services.pdf_storage import store_pdf
from .compiler import compile_with_retry
from .letter_writer import write_application_cover_letter
from .rewriter import rewrite_resume


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
