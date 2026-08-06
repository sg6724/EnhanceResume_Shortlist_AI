from __future__ import annotations

from app.agents import orchestrator
from tests.fakes import FakeSupabase


async def test_run_manual_match_drafts_a_cover_letter(monkeypatch):
    sb = FakeSupabase()
    await sb.table("users").insert({
        "id": "u1", "match_threshold": 0.6, "max_compiler_retries": 3,
    }).execute()
    await sb.table("master_resume").insert({
        "user_id": "u1", "tex_content": r"\documentclass{article}\begin{document}X\end{document}",
        "plain_text_cache": "MASTER TEXT", "version": 1,
    }).execute()
    jd_ins = await sb.table("scraped_jds").insert({
        "user_id": "u1", "source": "manual", "company": "Acme", "title": "Backend Engineer",
        "raw_text": "JD text", "must_have_skills": [], "nice_to_have_skills": [], "tech_stack": [],
    }).execute()
    jd_id = jd_ins.data[0]["id"]

    async def fake_compute_match(*args, **kwargs):
        return {
            "keyword_score": 0.5, "semantic_score": 0.5, "llm_score": 0.5, "composite_score": 0.5,
            "gap_analysis": "gaps", "matched_skills": [], "missing_skills": [],
        }

    async def fake_tailor_and_draft(*, jd, master, user, sb, http, match_data, origin):
        assert origin == "quick_match"
        return {"copy_id": "c1", "target_id": "t1", "draft_id": "d1", "status": "drafted"}

    monkeypatch.setattr(orchestrator, "compute_match", fake_compute_match)
    monkeypatch.setattr(orchestrator, "tailor_and_draft", fake_tailor_and_draft)

    result = await orchestrator.run_manual_match(jd_id, sb, object())

    assert result["status"] == "drafted"
    assert result["draft_id"] == "d1"
    assert result["target_id"] == "t1"
