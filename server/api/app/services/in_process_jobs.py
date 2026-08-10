from __future__ import annotations

from datetime import datetime, timezone

import httpx
from supabase import acreate_client

from ..agents.application_prep import retry_target, run_application_prep
from ..agents.orchestrator import run_manual_match
from ..config import settings

_quick_match_jobs: set[str] = set()
_application_runs: set[str] = set()
_retry_targets: set[str] = set()


def is_quick_match_running(jd_id: str) -> bool:
    return jd_id in _quick_match_jobs


def is_application_run_running(run_id: str) -> bool:
    return run_id in _application_runs


async def _log_trace(sb, jd_id: str | None, agent: str, log: str, reasoning: str = "") -> None:
    await sb.table("agent_traces").insert({
        "jd_id": jd_id,
        "agent_name": agent,
        "log": log[:2000],
        "reasoning": reasoning[:5000],
    }).execute()


async def _mark_quick_match_failed(sb, jd_id: str, error: Exception) -> None:
    jd_res = await sb.table("scraped_jds").select("*").eq("id", jd_id).maybe_single().execute()
    if not jd_res or not jd_res.data:
        return
    jd = jd_res.data
    user_id = jd["user_id"]
    mr_res = await (
        sb.table("master_resume").select("*").eq("user_id", user_id)
        .order("version", desc=True).limit(1).execute()
    )
    master = mr_res.data[0] if mr_res.data else {}
    await sb.table("resume_copies").insert({
        "jd_id": jd_id,
        "user_id": user_id,
        "master_resume_id": master.get("id"),
        "tex_content": master.get("tex_content") or "",
        "diff_patch": f"Quick Match failed before completion: {error}",
        "status": "failed",
    }).execute()


async def run_quick_match_in_process(jd_id: str) -> None:
    if jd_id in _quick_match_jobs:
        return
    _quick_match_jobs.add(jd_id)
    sb = await acreate_client(settings.supabase_url, settings.supabase_service_key)
    http = httpx.AsyncClient(timeout=150.0)
    try:
        result = await run_manual_match(jd_id, sb, http)
        print(f"[in-process:quick_match] {result}")
    except Exception as e:
        print(f"[in-process:quick_match] failed for {jd_id}: {e!r}")
        try:
            await _log_trace(sb, jd_id, "quick_match", f"Quick Match failed: {e}", repr(e))
            await _mark_quick_match_failed(sb, jd_id, e)
        except Exception as cleanup_error:
            print(f"[in-process:quick_match] failure cleanup failed for {jd_id}: {cleanup_error!r}")
    finally:
        await http.aclose()
        _quick_match_jobs.discard(jd_id)


async def run_application_prep_in_process(
    run_id: str,
    user_id: str,
    career_urls: list[str] | None = None,
    linkedin_urls: list[str] | None = None,
    x_urls: list[str] | None = None,
) -> None:
    if run_id in _application_runs:
        return
    _application_runs.add(run_id)
    sb = await acreate_client(settings.supabase_url, settings.supabase_service_key)
    http = httpx.AsyncClient(timeout=280.0)
    try:
        result = await run_application_prep(
            run_id,
            user_id,
            sb,
            http,
            career_urls=career_urls or [],
            linkedin_urls=linkedin_urls or [],
            x_urls=x_urls or [],
        )
        print(f"[in-process:application_prep] {result}")
    except Exception as e:
        print(f"[in-process:application_prep] failed for {run_id}: {e!r}")
        await sb.table("application_runs").update({
            "status": "failed",
            "error": str(e)[:1000],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", run_id).execute()
    finally:
        await http.aclose()
        _application_runs.discard(run_id)


async def retry_target_in_process(target_id: str) -> None:
    if target_id in _retry_targets:
        return
    _retry_targets.add(target_id)
    sb = await acreate_client(settings.supabase_url, settings.supabase_service_key)
    http = httpx.AsyncClient(timeout=150.0)
    try:
        result = await retry_target(target_id, sb, http)
        print(f"[in-process:retry_target] {result}")
    except Exception as e:
        print(f"[in-process:retry_target] failed for {target_id}: {e!r}")
    finally:
        await http.aclose()
        _retry_targets.discard(target_id)
