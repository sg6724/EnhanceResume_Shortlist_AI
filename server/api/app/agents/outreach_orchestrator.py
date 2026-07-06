from __future__ import annotations

from datetime import datetime, timezone

import httpx
from supabase import AsyncClient

from ..compile_client import compile_tex
from ..config import settings
from ..services.email import send_outreach_email
from .contact_finder import find_contact
from .letter_writer import write_letter

MAX_DRAFT_ATTEMPTS = 3


async def _log(sb: AsyncClient, jd_id: str | None, agent: str, log: str, reasoning: str = "") -> None:
    await sb.table("agent_traces").insert({
        "jd_id": jd_id, "agent_name": agent,
        "log": log[:2000], "reasoning": reasoning[:5000],
    }).execute()


async def _ingest_pipeline_companies(user_id: str, sb: AsyncClient, threshold: float) -> int:
    """Create pending targets for companies behind above-threshold matches."""
    matches = await (
        sb.table("jd_matches")
        .select("composite_score, jd_id, scraped_jds(id, company, title)")
        .eq("user_id", user_id).gte("composite_score", threshold)
        .execute()
    )
    existing = await sb.table("outreach_targets").select("company_name").eq("user_id", user_id).execute()
    known = {t["company_name"].lower() for t in existing.data}
    created = 0
    for m in matches.data:
        jd = m.get("scraped_jds") or {}
        company = (jd.get("company") or "").strip()
        if not company or company.lower() in known:
            continue
        await sb.table("outreach_targets").insert({
            "user_id": user_id, "company_name": company, "source": "pipeline",
            "jd_id": jd["id"], "role_title": jd.get("title", ""), "status": "pending",
        }).execute()
        known.add(company.lower())
        created += 1
    return created


async def run_outreach_cycle(user_id: str, sb: AsyncClient, http: httpx.AsyncClient) -> dict:
    """One cron cycle: ingest -> find contacts -> draft letters (batch-limited)."""
    user_res = await sb.table("users").select("*").eq("id", user_id).maybe_single().execute()
    if not user_res.data:
        return {"error": "user not found"}
    user = user_res.data
    if not user.get("outreach_enabled", True):
        return {"skipped": "outreach disabled"}

    ingested = await _ingest_pipeline_companies(user_id, sb, user["match_threshold"])

    mr_res = await (
        sb.table("master_resume").select("plain_text_cache").eq("user_id", user_id)
        .order("version", desc=True).limit(1).execute()
    )
    resume_text = mr_res.data[0]["plain_text_cache"] if mr_res.data else ""

    # 'contact_found' included so failed letter drafts get retried next cycle
    pending = await (
        sb.table("outreach_targets").select("*").eq("user_id", user_id)
        .in_("status", ["pending", "contact_found"]).lt("attempts", MAX_DRAFT_ATTEMPTS)
        .order("created_at").limit(user.get("outreach_batch_size", 3))
        .execute()
    )

    found = drafted = failed = 0
    for target in pending.data:
        try:
            tid = target["id"]
            await sb.table("outreach_targets").update(
                {"attempts": target["attempts"] + 1, "updated_at": datetime.now(timezone.utc).isoformat()}
            ).eq("id", tid).execute()

            if target["status"] == "contact_found":
                # Contact already known (earlier cycle or manual entry) — only drafting remains
                contact = {"found": True, "company_domain": target.get("company_domain"),
                           "founder_name": target.get("founder_name") or "there",
                           "founder_title": target.get("founder_title") or "",
                           "founder_email": target["founder_email"]}
            else:
                contact = await find_contact(http, sb, target["company_name"], target.get("company_domain"))
                if not contact["found"]:
                    await sb.table("outreach_targets").update({
                        "status": "contact_not_found",
                        "company_domain": contact.get("company_domain"),
                        "failure_reason": contact.get("failure_reason", ""),
                    }).eq("id", tid).execute()
                    await _log(sb, target.get("jd_id"), "contact_finder",
                               f"{target['company_name']}: {contact.get('failure_reason', '')}")
                    failed += 1
                    continue

                await sb.table("outreach_targets").update({
                    "status": "contact_found",
                    "company_domain": contact["company_domain"],
                    "founder_name": contact["founder_name"],
                    "founder_title": contact["founder_title"],
                    "founder_email": contact["founder_email"],
                    "email_confidence": contact["email_confidence"],
                    "contact_method": contact["contact_method"],
                }).eq("id", tid).execute()
                await _log(sb, target.get("jd_id"), "contact_finder",
                           f"{target['company_name']}: {contact['founder_name']} "
                           f"<{contact['founder_email']}> ({contact['email_confidence']})")
                found += 1

            # Draft the letter
            jd_text = ""
            resume_copy_id = None
            if target.get("jd_id"):
                jd_res = await sb.table("scraped_jds").select("raw_text").eq("id", target["jd_id"]).maybe_single().execute()
                jd_text = jd_res.data["raw_text"] if jd_res and jd_res.data else ""
                copy_res = await (
                    sb.table("resume_copies").select("id").eq("jd_id", target["jd_id"])
                    .eq("status", "compiled").order("created_at", desc=True).limit(1).execute()
                )
                if copy_res.data:
                    resume_copy_id = copy_res.data[0]["id"]

            role = target.get("role_title") or ""
            if not role:
                pos_res = await (
                    sb.table("target_positions").select("title").eq("user_id", user_id)
                    .eq("is_active", True).limit(1).execute()
                )
                role = pos_res.data[0]["title"] if pos_res.data else "an engineering role"

            try:
                subject, body = await write_letter(
                    resume_text=resume_text, jd_text=jd_text, role_title=role,
                    founder_name=contact["founder_name"], founder_title=contact["founder_title"],
                    company_name=target["company_name"],
                )
            except Exception as e:
                await _log(sb, target.get("jd_id"), "letter_writer", f"draft failed: {e}")
                continue  # stays contact_found; retried next cycle (attempts capped)

            await sb.table("outreach_drafts").insert({
                "target_id": tid, "subject": subject, "body": body,
                "resume_copy_id": resume_copy_id,
            }).execute()
            await sb.table("outreach_targets").update({"status": "drafted"}).eq("id", tid).execute()
            await _log(sb, target.get("jd_id"), "letter_writer",
                       f"drafted for {target['company_name']}: {subject}")
            drafted += 1
        except Exception as e:
            await _log(sb, target.get("jd_id"), "outreach_orchestrator",
                       f"target {target['company_name']} failed: {e}")
            continue

    await sb.table("users").update(
        {"outreach_last_run_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", user_id).execute()

    return {"ingested": ingested, "processed": len(pending.data),
            "contacts_found": found, "drafted": drafted, "not_found": failed}


async def send_outreach(draft_id: str, sb: AsyncClient, http: httpx.AsyncClient) -> dict:
    """Compile the PDF, send via Resend, update statuses. Called by the worker."""
    draft_res = await (
        sb.table("outreach_drafts").select("*, outreach_targets(*)")
        .eq("id", draft_id).maybe_single().execute()
    )
    if not draft_res.data:
        return {"error": "draft not found"}
    draft = draft_res.data
    target = draft["outreach_targets"]
    if target["status"] != "approved":
        return {"error": f"target status is '{target['status']}', not 'approved'"}

    # Pick tex: tailored copy when available, else master
    tex = None
    if draft.get("resume_copy_id"):
        copy_res = await sb.table("resume_copies").select("tex_content").eq("id", draft["resume_copy_id"]).maybe_single().execute()
        if copy_res and copy_res.data:
            tex = copy_res.data["tex_content"]
    if tex is None:
        mr_res = await (
            sb.table("master_resume").select("tex_content").eq("user_id", target["user_id"])
            .order("version", desc=True).limit(1).execute()
        )
        tex = mr_res.data[0]["tex_content"] if mr_res.data else None

    pdf_bytes = None
    if tex:
        resp = await compile_tex(http, tex)
        if resp.status_code == 200:
            pdf_bytes = resp.content
        else:
            print(f"[outreach] compile failed ({resp.status_code}); sending without attachment")
            await _log(sb, target.get("jd_id"), "compiler",
                       f"compile failed ({resp.status_code}); sending without attachment")

    subject = draft.get("edited_subject") or draft["subject"]
    body = draft.get("edited_body") or draft["body"]
    try:
        msg_id = send_outreach_email(
            to=target["founder_email"], subject=subject, body_text=body,
            pdf_bytes=pdf_bytes,
            pdf_filename=f"resume-{target['company_name'].lower().replace(' ', '-')}.pdf",
        )
    except Exception as e:
        await sb.table("outreach_drafts").update({"send_error": str(e)[:500]}).eq("id", draft_id).execute()
        await _log(sb, target.get("jd_id"), "outreach_sender", f"send FAILED: {e}")
        return {"error": f"send failed: {e}"}

    now = datetime.now(timezone.utc).isoformat()
    await sb.table("outreach_drafts").update({
        "sent_at": now, "resend_message_id": msg_id, "send_error": None,
    }).eq("id", draft_id).execute()
    await sb.table("outreach_targets").update({"status": "sent"}).eq("id", target["id"]).execute()
    await _log(sb, target.get("jd_id"), "outreach_sender",
               f"sent to {target['founder_email']} (resend {msg_id})")
    return {"sent": True, "resend_message_id": msg_id}
