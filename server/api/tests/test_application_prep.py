from __future__ import annotations

from app.agents import application_prep
from tests.fakes import FakeSupabase

JD = {
    "id": "jd1", "user_id": "u1", "title": "Backend Engineer", "company": "Acme",
    "raw_text": "We need a backend engineer.",
}
MASTER = {"id": "m1", "tex_content": r"\documentclass{article}\begin{document}X\end{document}", "plain_text_cache": "MASTER PLAIN TEXT"}
USER = {"max_compiler_retries": 3}
MATCH_DATA = {"composite_score": 0.9, "gap_analysis": "no gaps"}


def _patch_success(monkeypatch, tailored_text="TAILORED PLAIN TEXT"):
    async def fake_rewrite(**kwargs):
        return r"\documentclass{article}\begin{document}Y\end{document}", "DIFF:\n- changed"

    async def fake_compile(**kwargs):
        return b"%PDF-fake", kwargs["tex"], ""

    async def fake_store_pdf(sb, user_id, copy_id, pdf_bytes):
        return f"{user_id}/{copy_id}.pdf"

    def fake_tex_to_plaintext(tex):
        return tailored_text

    async def fake_write_letter(*, resume_text, jd_text, role_title, company_name):
        fake_write_letter.last_resume_text = resume_text
        return "Subject line", "Body of the letter."

    monkeypatch.setattr(application_prep, "rewrite_resume", fake_rewrite)
    monkeypatch.setattr(application_prep, "compile_with_retry", fake_compile)
    monkeypatch.setattr(application_prep, "store_pdf", fake_store_pdf)
    monkeypatch.setattr(application_prep, "tex_to_plaintext", fake_tex_to_plaintext)
    monkeypatch.setattr(application_prep, "write_application_cover_letter", fake_write_letter)
    return fake_write_letter


async def test_tailor_and_draft_creates_target_and_draft_from_tailored_resume(monkeypatch):
    fake_letter = _patch_success(monkeypatch)
    sb = FakeSupabase()

    result = await application_prep.tailor_and_draft(
        jd=JD, master=MASTER, user=USER, sb=sb, http=object(),
        match_data=MATCH_DATA, origin="career_page",
    )

    assert result["status"] == "drafted"
    assert result["draft_id"] is not None
    target = sb.tables["outreach_targets"][0]
    assert target["company_name"] == "Acme"
    assert target["source"] == "career_page"
    assert target["status"] == "drafted"
    draft = sb.tables["outreach_drafts"][0]
    assert draft["subject"] == "Subject line"
    assert draft["resume_copy_id"] == result["copy_id"]
    # the letter must be drafted from the TAILORED resume, not the master's plain_text_cache
    assert fake_letter.last_resume_text == "TAILORED PLAIN TEXT"


async def test_tailor_and_draft_always_drafts_regardless_of_score(monkeypatch):
    _patch_success(monkeypatch)
    sb = FakeSupabase()

    low_score_match = {"composite_score": 0.05, "gap_analysis": "big gaps"}
    result = await application_prep.tailor_and_draft(
        jd=JD, master=MASTER, user=USER, sb=sb, http=object(),
        match_data=low_score_match, origin="career_page",
    )

    assert result["status"] == "drafted"


async def test_tailor_and_draft_falls_back_to_master_text_when_compile_fails(monkeypatch):
    fake_letter = _patch_success(monkeypatch)

    async def fake_compile_fails(**kwargs):
        return None, kwargs["tex"], "pdflatex error"

    monkeypatch.setattr(application_prep, "compile_with_retry", fake_compile_fails)
    sb = FakeSupabase()

    result = await application_prep.tailor_and_draft(
        jd=JD, master=MASTER, user=USER, sb=sb, http=object(),
        match_data=MATCH_DATA, origin="career_page",
    )

    assert result["status"] == "drafted"
    assert fake_letter.last_resume_text == "MASTER PLAIN TEXT"
    draft = sb.tables["outreach_drafts"][0]
    assert draft["resume_copy_id"] is None


async def test_tailor_and_draft_marks_target_failed_when_letter_generation_raises(monkeypatch):
    _patch_success(monkeypatch)

    async def fake_write_letter_raises(**kwargs):
        raise ValueError("letter generation failed after 2 attempts")

    monkeypatch.setattr(application_prep, "write_application_cover_letter", fake_write_letter_raises)
    sb = FakeSupabase()

    result = await application_prep.tailor_and_draft(
        jd=JD, master=MASTER, user=USER, sb=sb, http=object(),
        match_data=MATCH_DATA, origin="career_page",
    )

    assert result["status"] == "failed"
    assert result["draft_id"] is None
    target = sb.tables["outreach_targets"][0]
    assert target["status"] == "failed"
    assert target["failure_reason"]
    assert sb.tables.get("outreach_drafts", []) == []


class _FakeExtracted:
    def __init__(self, role_title="Backend Engineer"):
        self.role_title = role_title
        self.seniority = "mid"
        self.responsibilities = ["build things"]
        self.must_have_skills = ["python"]
        self.nice_to_have_skills = ["go"]
        self.tech_stack = ["fastapi"]


def _raw_jd(company="Acme", title="Backend Engineer", dedup_hash="hash-1", source="career_page"):
    return {
        "source": source, "company": company, "title": title, "location": "Remote",
        "url": f"https://{company.lower()}.com/careers/1", "raw_text": f"{title} at {company}. " * 10,
        "dedup_hash": dedup_hash,
    }


def _patch_pipeline(monkeypatch, raw_jds, tailor_results=None):
    async def fake_scrape_jds(keywords, **kwargs):
        return raw_jds

    async def fake_extract(raw_text):
        return _FakeExtracted()

    async def fake_compute_match(*args, **kwargs):
        return {
            "keyword_score": 0.5, "semantic_score": 0.5, "llm_score": 0.5, "composite_score": 0.5,
            "gap_analysis": "gaps", "matched_skills": ["python"], "missing_skills": [],
        }

    calls: list[str] = []

    async def fake_tailor_and_draft(*, jd, master, user, sb, http, match_data, origin):
        calls.append(jd["id"])
        status = "drafted"
        if tailor_results:
            status = tailor_results.pop(0)
        target_ins = await sb.table("outreach_targets").insert({
            "user_id": jd["user_id"], "company_name": jd["company"], "source": origin,
            "jd_id": jd["id"], "role_title": jd["title"], "status": status,
        }).execute()
        return {"copy_id": "c1", "target_id": target_ins.data[0]["id"],
                "draft_id": "d1" if status == "drafted" else None, "status": status}

    monkeypatch.setattr(application_prep, "scrape_jds", fake_scrape_jds)
    monkeypatch.setattr(application_prep, "extract_jd_structured", fake_extract)
    monkeypatch.setattr(application_prep, "compute_match", fake_compute_match)
    monkeypatch.setattr(application_prep, "tailor_and_draft", fake_tailor_and_draft)
    return calls


async def _seed_user_and_resume(sb, user_id="u1"):
    await sb.table("users").insert({"id": user_id, "max_compiler_retries": 3}).execute()
    await sb.table("master_resume").insert({
        "user_id": user_id, "tex_content": r"\documentclass{article}\begin{document}X\end{document}",
        "plain_text_cache": "MASTER TEXT", "version": 1,
    }).execute()


async def test_run_application_prep_happy_path(monkeypatch):
    sb = FakeSupabase()
    await _seed_user_and_resume(sb)
    run_ins = await sb.table("application_runs").insert({"user_id": "u1", "status": "running"}).execute()
    run_id = run_ins.data[0]["id"]

    calls = _patch_pipeline(monkeypatch, [_raw_jd("Acme"), _raw_jd("Globex", dedup_hash="hash-2")])

    result = await application_prep.run_application_prep(
        run_id, "u1", sb, object(), career_urls=["https://acme.com/careers"], linkedin_urls=[], x_urls=[],
    )

    assert result["jds_found"] == 2
    assert result["targets_drafted"] == 2
    assert len(calls) == 2
    run = sb.tables["application_runs"][0]
    assert run["status"] == "done"
    assert run["jds_done"] == 2


async def test_run_application_prep_skips_jd_already_targeted(monkeypatch):
    sb = FakeSupabase()
    await _seed_user_and_resume(sb)
    # Pre-existing scraped_jds row with the SAME dedup_hash the scrape will produce,
    # plus an outreach_targets row already pointing at it.
    jd_ins = await sb.table("scraped_jds").insert({
        "user_id": "u1", "source": "career_page", "company": "Acme", "title": "Backend Engineer",
        "raw_text": "old", "dedup_hash": "hash-1",
    }).execute()
    existing_jd_id = jd_ins.data[0]["id"]
    await sb.table("outreach_targets").insert({
        "user_id": "u1", "company_name": "Acme", "source": "career_page",
        "jd_id": existing_jd_id, "role_title": "Backend Engineer", "status": "drafted",
    }).execute()
    run_ins = await sb.table("application_runs").insert({"user_id": "u1", "status": "running"}).execute()
    run_id = run_ins.data[0]["id"]

    calls = _patch_pipeline(monkeypatch, [_raw_jd("Acme", dedup_hash="hash-1")])

    result = await application_prep.run_application_prep(
        run_id, "u1", sb, object(), career_urls=["https://acme.com/careers"], linkedin_urls=[], x_urls=[],
    )

    assert len(calls) == 0  # never re-tailored — already targeted
    assert result["jds_done"] == 1
    assert result["targets_drafted"] == 0


async def test_run_application_prep_continues_after_one_jd_fails(monkeypatch):
    sb = FakeSupabase()
    await _seed_user_and_resume(sb)
    run_ins = await sb.table("application_runs").insert({"user_id": "u1", "status": "running"}).execute()
    run_id = run_ins.data[0]["id"]

    _patch_pipeline(
        monkeypatch,
        [_raw_jd("Acme"), _raw_jd("Globex", dedup_hash="hash-2")],
        tailor_results=["failed", "drafted"],
    )

    result = await application_prep.run_application_prep(
        run_id, "u1", sb, object(), career_urls=["https://acme.com/careers"], linkedin_urls=[], x_urls=[],
    )

    assert result["targets_failed"] == 1
    assert result["targets_drafted"] == 1
    run = sb.tables["application_runs"][0]
    assert run["status"] == "done"  # one bad JD does not fail the whole run


async def test_run_application_prep_fails_run_when_no_master_resume(monkeypatch):
    sb = FakeSupabase()
    await sb.table("users").insert({"id": "u1", "max_compiler_retries": 3}).execute()
    run_ins = await sb.table("application_runs").insert({"user_id": "u1", "status": "running"}).execute()
    run_id = run_ins.data[0]["id"]
    _patch_pipeline(monkeypatch, [_raw_jd("Acme")])

    result = await application_prep.run_application_prep(
        run_id, "u1", sb, object(), career_urls=["https://acme.com/careers"], linkedin_urls=[], x_urls=[],
    )

    assert "error" in result
    run = sb.tables["application_runs"][0]
    assert run["status"] == "failed"


async def test_retry_target_deletes_old_target_and_recreates_it(monkeypatch):
    sb = FakeSupabase()
    await _seed_user_and_resume(sb)
    jd_ins = await sb.table("scraped_jds").insert({
        "user_id": "u1", "source": "career_page", "company": "Acme", "title": "Backend Engineer",
        "raw_text": "jd text", "dedup_hash": "hash-1",
    }).execute()
    jd_id = jd_ins.data[0]["id"]
    target_ins = await sb.table("outreach_targets").insert({
        "user_id": "u1", "company_name": "Acme", "source": "career_page",
        "jd_id": jd_id, "role_title": "Backend Engineer", "status": "failed", "attempts": 1,
    }).execute()
    old_target_id = target_ins.data[0]["id"]

    async def fake_tailor_and_draft(*, jd, master, user, sb, http, match_data, origin):
        ins = await sb.table("outreach_targets").insert({
            "user_id": "u1", "company_name": "Acme", "source": origin,
            "jd_id": jd["id"], "role_title": jd["title"], "status": "drafted",
        }).execute()
        return {"copy_id": "c1", "target_id": ins.data[0]["id"], "draft_id": "d1", "status": "drafted"}

    monkeypatch.setattr(application_prep, "tailor_and_draft", fake_tailor_and_draft)

    result = await application_prep.retry_target(old_target_id, sb, object())

    assert result["status"] == "drafted"
    assert not any(t["id"] == old_target_id for t in sb.tables["outreach_targets"])
    new_target = next(t for t in sb.tables["outreach_targets"] if t["jd_id"] == jd_id)
    assert new_target["attempts"] == 2
