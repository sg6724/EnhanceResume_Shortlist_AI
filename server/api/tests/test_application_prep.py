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
