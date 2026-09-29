from __future__ import annotations

from app.services import in_process_jobs
from tests.fakes import FakeSupabase


async def test_quick_match_failure_keeps_provider_error_out_of_copy_diff():
    """The raw provider error belongs in agent_traces (Traces page), not in the
    resume copy's diff_patch, which the Copies page renders as its subtitle."""
    sb = FakeSupabase()
    sb.tables["scraped_jds"] = [{"id": "jd1", "user_id": "u1"}]
    sb.tables["master_resume"] = [{"id": "m1", "user_id": "u1", "version": 1, "tex_content": "tex"}]

    await in_process_jobs._mark_quick_match_failed(sb, "jd1")

    copy = sb.tables["resume_copies"][0]
    assert copy["status"] == "failed"
    assert not copy.get("diff_patch")
