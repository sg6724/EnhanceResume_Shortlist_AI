from app.domain.models import (
    AgentTrace,
    Checkpoint,
    Contact,
    CompileResult,
    JdMatch,
    MasterResume,
    OutreachDraft,
    OutreachTarget,
    Position,
    QuotaUsage,
    RawJd,
    ResumeCopy,
    ScorerResult,
    ScrapedJd,
    User,
)


def test_position_defaults_and_parsing():
    p = Position(id="p1", user_id="u1", title="AI Engineer",
                 created_at="2026-07-09T00:00:00+00:00")
    assert p.fuzzy_keywords == []
    assert p.is_active is True
    assert p.created_at.year == 2026


def test_position_with_keywords():
    p = Position(id="p1", title="AI Engineer", fuzzy_keywords=["ML Engineer", "LLM Engineer"])
    assert p.fuzzy_keywords == ["ML Engineer", "LLM Engineer"]


def test_master_resume_round_trip():
    row = {
        "id": "m1", "user_id": "u1", "tex_content": "\\documentclass{article}",
        "plain_text_cache": "hello", "version": 2, "created_at": "2026-07-09T00:00:00+00:00",
    }
    mr = MasterResume(**row)
    assert mr.version == 2
    assert mr.plain_text_cache == "hello"


def test_scraped_jd_optional_fields_default_none():
    jd = ScrapedJd(id="j1", source="remoteok", title="AI Engineer", raw_text="text " * 30)
    assert jd.company is None
    assert jd.dedup_hash is None


def test_jd_match_scores_optional():
    m = JdMatch(id="mm1")
    assert m.composite_score is None
    assert m.gap_analysis is None


def test_checkpoint_status_default_pending():
    c = Checkpoint(id="c1")
    assert c.status == "pending"


def test_resume_copy_defaults():
    rc = ResumeCopy(id="rc1")
    assert rc.status == "pending_approval"
    assert rc.is_applied is False


def test_outreach_target_defaults():
    t = OutreachTarget(id="t1", company_name="Acme")
    assert t.status == "pending"
    assert t.source == "watchlist"
    assert t.attempts == 0


def test_outreach_draft_requires_target_subject_body():
    d = OutreachDraft(id="d1", target_id="t1", subject="Hi", body="Body text")
    assert d.sent_at is None
    assert d.send_error is None


def test_agent_trace_minimal():
    tr = AgentTrace(id="tr1", agent_name="matcher")
    assert tr.log is None


def test_quota_usage_defaults():
    q = QuotaUsage(provider="apollo", month="2026-07")
    assert q.count == 0


def test_user_defaults_match_current_db_defaults():
    u = User(id="u1", email="a@b.com")
    assert u.match_threshold == 0.6
    assert u.top_n == 5
    assert u.outreach_enabled is True
    assert u.outreach_batch_size == 3
    assert u.max_resume_versions == 3
    assert u.max_semantic_distance == 0.8
    assert u.scraper_delay_ms == 2000
    assert u.created_at is None


def test_contact_value_object():
    c = Contact(company_domain="acme.com", founder_name="Ada Ng", founder_title="CTO",
                founder_email="ada@acme.com", email_confidence="verified", contact_method="apollo")
    assert c.contact_method == "apollo"


def test_raw_jd_defaults():
    r = RawJd(source="remoteok", company="Acme", title="AI Engineer", raw_text="x" * 200)
    assert r.location == "Remote"
    assert r.url == ""


def test_compile_result_failure_shape():
    r = CompileResult(success=False, error_log="pdflatex error")
    assert r.pdf_bytes is None


def test_scorer_result_shape():
    r = ScorerResult(name="bm25", score=0.42)
    assert r.detail == ""
