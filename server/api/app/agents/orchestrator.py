from __future__ import annotations

import httpx
from supabase import AsyncClient

from ..config import settings
from ..services.email import notify_batch_complete
from ..services.pdf_storage import store_pdf
from .scraper import scrape_jds
from .filter_agent import is_jd_relevant
from .matcher import compute_match
from .rewriter import rewrite_resume
from .compiler import compile_with_retry


async def _log(sb: AsyncClient, jd_id: str, agent: str, log: str, reasoning: str = "") -> None:
    await sb.table("agent_traces").insert({
        "jd_id": jd_id,
        "agent_name": agent,
        "log": log[:2000],
        "reasoning": reasoning[:5000],
    }).execute()


async def run_pipeline(user_id: str, sb: AsyncClient, http: httpx.AsyncClient) -> dict:
    """
    Full pipeline: scrape → filter → match → create checkpoints.
    Top N are surfaced to the user; rest are auto-approved and queued.
    """
    # Load user config
    user_res = await sb.table("users").select("*").eq("id", user_id).maybe_single().execute()
    if not user_res.data:
        return {"error": "user not found"}
    user = user_res.data
    match_threshold: float = user["match_threshold"]
    top_n: int = user["top_n"]

    # Load active positions
    pos_res = await sb.table("target_positions").select("*").eq("user_id", user_id).eq("is_active", True).execute()
    positions = pos_res.data
    if not positions:
        return {"error": "no active target positions"}

    # Load latest master resume
    mr_res = await (
        sb.table("master_resume").select("*").eq("user_id", user_id)
        .order("version", desc=True).limit(1).execute()
    )
    if not mr_res.data:
        return {"error": "no master resume uploaded"}
    master = mr_res.data[0]

    # Build keyword list
    all_keywords: list[str] = []
    for p in positions:
        all_keywords.append(p["title"])
        all_keywords.extend(p.get("fuzzy_keywords") or [])
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_kws: list[str] = []
    for kw in all_keywords:
        if kw.lower() not in seen:
            seen.add(kw.lower())
            unique_kws.append(kw)

    print(f"[orchestrator] Scraping for: {unique_kws[:6]}")
    jds = await scrape_jds(unique_kws)
    print(f"[orchestrator] Got {len(jds)} valid JDs")

    target_titles = [p["title"] for p in positions]

    # Process each JD
    above_threshold: list[tuple[float, dict, dict]] = []  # (score, jd_row, match_data)

    for jd in jds:
        # Filter gate
        relevant, reason = await is_jd_relevant(jd["raw_text"], target_titles)
        if not relevant:
            print(f"[filter] Rejected: {jd['title']} — {reason}")
            continue

        # Upsert JD record
        jd_ins = await sb.table("scraped_jds").upsert({
            "user_id": user_id,
            "source": jd["source"],
            "company": jd["company"],
            "title": jd["title"],
            "location": jd.get("location", ""),
            "url": jd.get("url", ""),
            "raw_text": jd["raw_text"],
            "relevance_confirmed": True,
            "dedup_hash": jd["dedup_hash"],
        }, on_conflict="dedup_hash").execute()
        jd_row = jd_ins.data[0]
        jd_id = jd_row["id"]

        await _log(sb, jd_id, "filter", f"Passed filter: {reason}")

        # Score against each applicable position
        for pos in positions:
            pos_title: str = pos["title"]
            pos_kws: list[str] = pos.get("fuzzy_keywords") or []
            title_lower = jd["title"].lower()
            if pos_title.lower() in title_lower or any(k.lower() in title_lower for k in pos_kws):
                position_context = pos_title
            else:
                position_context = target_titles[0]

            match_data = await compute_match(jd["raw_text"], master["plain_text_cache"], position_context)
            match_ins = await sb.table("jd_matches").insert({
                "jd_id": jd_id,
                "user_id": user_id,
                "position_context": position_context,
                **match_data,
            }).execute()
            match_row = match_ins.data[0]

            await _log(sb, jd_id, "matcher",
                       f"Score: {match_data['composite_score']:.2f} | {position_context}",
                       match_data.get("gap_analysis", ""))

            if match_data["composite_score"] >= match_threshold:
                above_threshold.append((match_data["composite_score"], jd_row, {
                    **match_data, "match_id": match_row["id"]
                }))

    # Sort descending by composite score
    above_threshold.sort(key=lambda x: x[0], reverse=True)
    top = above_threshold[:top_n]
    rest = above_threshold[top_n:]

    # Create pending checkpoints for top N (user must approve)
    for _, jd_row, match_data in top:
        planned_diff = (
            f"Job: {jd_row['title']} at {jd_row['company']}\n"
            f"Source: {jd_row.get('source', '?')}\n"
            f"Composite score: {match_data['composite_score']:.0%}\n\n"
            f"Planned changes:\n{match_data.get('gap_analysis', 'See gap analysis')}"
        )
        cp_ins = await sb.table("checkpoint_state").insert({
            "jd_id": jd_row["id"],
            "user_id": user_id,
            "planned_diff": planned_diff,
            "status": "pending",
        }).execute()
        await _log(sb, jd_row["id"], "orchestrator",
                   f"Checkpoint created: {cp_ins.data[0]['id']}")

    # Auto-approve rest and queue directly
    from ..queue import rewrite_resume_task
    for _, jd_row, match_data in rest:
        planned_diff = (
            f"[Background] {jd_row['title']} at {jd_row['company']}\n"
            f"Score: {match_data['composite_score']:.0%}"
        )
        cp_ins = await sb.table("checkpoint_state").insert({
            "jd_id": jd_row["id"],
            "user_id": user_id,
            "planned_diff": planned_diff,
            "status": "approved",
        }).execute()
        cp_id = cp_ins.data[0]["id"]
        await rewrite_resume_task.defer_async(checkpoint_id=cp_id)

    total = len(above_threshold)
    notify_batch_complete(settings.user_email, total, zero_matches=(total == 0))

    return {
        "total_scraped": len(jds),
        "above_threshold": total,
        "pending_checkpoints": len(top),
        "queued_background": len(rest),
    }


async def run_rewrite(checkpoint_id: str, sb: AsyncClient, http: httpx.AsyncClient) -> dict:
    """
    Execute resume rewrite + compile for an approved checkpoint.
    Called by the Procrastinate worker.
    """
    cp_res = await (
        sb.table("checkpoint_state")
        .select("*, scraped_jds(*)")
        .eq("id", checkpoint_id)
        .maybe_single()
        .execute()
    )
    if not cp_res.data:
        return {"error": "checkpoint not found"}
    if cp_res.data["status"] != "approved":
        return {"error": f"checkpoint status is '{cp_res.data['status']}', not 'approved'"}

    cp = cp_res.data
    jd = cp["scraped_jds"]
    jd_id = jd["id"]
    user_id = cp["user_id"]

    # Load user + master resume
    user_res = await sb.table("users").select("*").eq("id", user_id).maybe_single().execute()
    user = user_res.data
    mr_res = await (
        sb.table("master_resume").select("*").eq("user_id", user_id)
        .order("version", desc=True).limit(1).execute()
    )
    if not mr_res.data:
        return {"error": "no master resume"}
    master = mr_res.data[0]

    # Get match data for gap analysis
    match_res = await (
        sb.table("jd_matches").select("*").eq("jd_id", jd_id).eq("user_id", user_id)
        .order("composite_score", desc=True).limit(1).execute()
    )
    match_info = match_res.data[0] if match_res.data else {}

    # Create resume copy record
    copy_ins = await sb.table("resume_copies").insert({
        "jd_id": jd_id,
        "user_id": user_id,
        "master_resume_id": master["id"],
        "status": "compiling",
        "tex_content": master["tex_content"],  # default to master until rewrite
    }).execute()
    copy_id = copy_ins.data[0]["id"]

    await _log(sb, jd_id, "rewriter", "Starting rewrite...")

    # Initial rewrite
    try:
        rewritten_tex, diff_summary = await rewrite_resume(
            master_tex=master["tex_content"],
            jd_text=jd["raw_text"],
            gap_analysis=match_info.get("gap_analysis", ""),
            position_context=match_info.get("position_context", ""),
        )
    except ValueError as e:
        await _log(sb, jd_id, "rewriter", f"Structure violation: {e}")
        rewritten_tex = master["tex_content"]
        diff_summary = f"Rewrite failed (structure violation): {e}"

    await _log(sb, jd_id, "rewriter", diff_summary[:300], diff_summary)

    # Compile with retry loop
    async def rewriter_fn(current_tex: str, error_log: str, attempt: int) -> tuple[str, str]:
        return await rewrite_resume(
            master_tex=current_tex,
            jd_text=jd["raw_text"],
            gap_analysis=match_info.get("gap_analysis", ""),
            position_context=match_info.get("position_context", ""),
            attempt=attempt,
            previous_error=error_log,
        )

    pdf_bytes, final_tex, error_log = await compile_with_retry(
        http=http,
        tex=rewritten_tex,
        rewriter_fn=rewriter_fn,
        max_retries=user.get("max_compiler_retries", 3),
        jd_info={"company": jd.get("company"), "title": jd.get("title")},
    )

    status = "compiled" if pdf_bytes else "failed"
    updates = {"tex_content": final_tex, "diff_patch": diff_summary, "status": status}
    if pdf_bytes:
        try:
            updates["pdf_storage_path"] = await store_pdf(sb, user_id, copy_id, pdf_bytes)
        except Exception as e:
            await _log(sb, jd_id, "compiler", f"PDF storage upload failed (non-fatal): {e}")
    await sb.table("resume_copies").update(updates).eq("id", copy_id).execute()

    if pdf_bytes:
        await _log(sb, jd_id, "compiler", f"PDF compiled successfully ({len(pdf_bytes):,} bytes)")
    else:
        await _log(sb, jd_id, "compiler", f"FAILED after all retries", error_log[:1000])

    return {"copy_id": copy_id, "status": status}


async def run_manual_match(jd_id: str, sb: AsyncClient, http: httpx.AsyncClient) -> dict:
    """
    On-demand score + rewrite + compile for one manually-submitted JD
    (Quick Match). No checkpoint gate — the user already expressed
    explicit intent by submitting this specific job. Mirrors run_rewrite's
    rewrite -> compile -> store chain, preceded by scoring.
    """
    jd_res = await sb.table("scraped_jds").select("*").eq("id", jd_id).maybe_single().execute()
    if not jd_res.data:
        return {"error": "JD not found"}
    jd = jd_res.data
    user_id = jd["user_id"]

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

    # Score — position context is the job's own title, no saved-Positions lookup
    match_data = await compute_match(jd["raw_text"], master["plain_text_cache"], jd["title"])
    match_ins = await sb.table("jd_matches").insert({
        "jd_id": jd_id,
        "user_id": user_id,
        "position_context": jd["title"],
        **match_data,
    }).execute()
    match_id = match_ins.data[0]["id"]
    await _log(sb, jd_id, "matcher",
               f"Score: {match_data['composite_score']:.2f} | {jd['title']}",
               match_data.get("gap_analysis", ""))

    # Straight to rewrite — no checkpoint
    copy_ins = await sb.table("resume_copies").insert({
        "jd_id": jd_id,
        "user_id": user_id,
        "master_resume_id": master["id"],
        "status": "compiling",
        "tex_content": master["tex_content"],
    }).execute()
    copy_id = copy_ins.data[0]["id"]

    await _log(sb, jd_id, "rewriter", "Starting rewrite...")

    try:
        rewritten_tex, diff_summary = await rewrite_resume(
            master_tex=master["tex_content"],
            jd_text=jd["raw_text"],
            gap_analysis=match_data.get("gap_analysis", ""),
            position_context=jd["title"],
        )
    except ValueError as e:
        await _log(sb, jd_id, "rewriter", f"Structure violation: {e}")
        rewritten_tex = master["tex_content"]
        diff_summary = f"Rewrite failed (structure violation): {e}"

    await _log(sb, jd_id, "rewriter", diff_summary[:300], diff_summary)

    async def rewriter_fn(current_tex: str, error_log: str, attempt: int) -> tuple[str, str]:
        return await rewrite_resume(
            master_tex=current_tex,
            jd_text=jd["raw_text"],
            gap_analysis=match_data.get("gap_analysis", ""),
            position_context=jd["title"],
            attempt=attempt,
            previous_error=error_log,
        )

    pdf_bytes, final_tex, error_log = await compile_with_retry(
        http=http,
        tex=rewritten_tex,
        rewriter_fn=rewriter_fn,
        max_retries=user.get("max_compiler_retries", 3),
        jd_info={"company": jd.get("company"), "title": jd.get("title")},
    )

    status = "compiled" if pdf_bytes else "failed"
    updates = {"tex_content": final_tex, "diff_patch": diff_summary, "status": status}
    if pdf_bytes:
        try:
            updates["pdf_storage_path"] = await store_pdf(sb, user_id, copy_id, pdf_bytes)
        except Exception as e:
            await _log(sb, jd_id, "compiler", f"PDF storage upload failed (non-fatal): {e}")
    await sb.table("resume_copies").update(updates).eq("id", copy_id).execute()

    return {"jd_id": jd_id, "match_id": match_id, "copy_id": copy_id, "status": status}
