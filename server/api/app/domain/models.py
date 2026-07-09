from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Position(BaseModel):
    id: str
    user_id: str | None = None
    title: str
    fuzzy_keywords: list[str] = []
    is_active: bool = True
    created_at: datetime | None = None


class MasterResume(BaseModel):
    id: str
    user_id: str | None = None
    tex_content: str
    plain_text_cache: str
    version: int = 1
    created_at: datetime | None = None


class ScrapedJd(BaseModel):
    id: str
    user_id: str | None = None
    source: str
    company: str | None = None
    title: str
    location: str | None = None
    url: str | None = None
    raw_text: str
    relevance_confirmed: bool | None = None
    dedup_hash: str | None = None
    scraped_at: datetime | None = None


class JdMatch(BaseModel):
    id: str
    jd_id: str | None = None
    user_id: str | None = None
    position_context: str | None = None
    keyword_score: float | None = None
    semantic_score: float | None = None
    llm_score: float | None = None
    composite_score: float | None = None
    gap_analysis: str | None = None
    created_at: datetime | None = None


class Checkpoint(BaseModel):
    id: str
    jd_id: str | None = None
    user_id: str | None = None
    planned_diff: str | None = None
    status: str = "pending"
    expires_at: datetime | None = None
    created_at: datetime | None = None


class ResumeCopy(BaseModel):
    id: str
    jd_id: str | None = None
    user_id: str | None = None
    master_resume_id: str | None = None
    tex_content: str | None = None
    diff_patch: str | None = None
    pdf_storage_path: str | None = None
    status: str = "pending_approval"
    is_applied: bool = False
    created_at: datetime | None = None


class OutreachTarget(BaseModel):
    id: str
    user_id: str | None = None
    company_name: str
    company_domain: str | None = None
    source: str = "watchlist"
    jd_id: str | None = None
    role_title: str | None = None
    status: str = "pending"
    founder_name: str | None = None
    founder_title: str | None = None
    founder_email: str | None = None
    email_confidence: str | None = None
    contact_method: str | None = None
    failure_reason: str | None = None
    attempts: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OutreachDraft(BaseModel):
    id: str
    target_id: str
    subject: str
    body: str
    edited_subject: str | None = None
    edited_body: str | None = None
    resume_copy_id: str | None = None
    sent_at: datetime | None = None
    resend_message_id: str | None = None
    send_error: str | None = None
    created_at: datetime | None = None


class AgentTrace(BaseModel):
    id: str
    jd_id: str | None = None
    agent_name: str
    log: str | None = None
    reasoning: str | None = None
    created_at: datetime | None = None


class QuotaUsage(BaseModel):
    id: str | None = None
    provider: str
    month: str
    count: int = 0


class User(BaseModel):
    id: str
    email: str
    match_threshold: float = 0.6
    top_n: int = 5
    timeout_minutes: int = 30
    max_compiler_retries: int = 3
    max_resume_versions: int = 3
    max_semantic_distance: float = 0.8
    scraper_delay_ms: int = 2000
    outreach_enabled: bool = True
    outreach_interval_hours: int = 24
    outreach_last_run_at: datetime | None = None
    outreach_batch_size: int = 3
    created_at: datetime | None = None


# --- Value objects (not DB rows) shared across integrations ---------------


class Contact(BaseModel):
    company_domain: str
    founder_name: str
    founder_title: str
    founder_email: str
    email_confidence: str  # "verified" | "guessed"
    contact_method: str  # "apollo" | "scraped" | "manual"


class RawJd(BaseModel):
    source: str
    company: str
    title: str
    location: str = "Remote"
    url: str = ""
    raw_text: str


class CompileResult(BaseModel):
    success: bool
    pdf_bytes: bytes | None = None
    error_log: str = ""


class ScorerResult(BaseModel):
    name: str
    score: float
    detail: str = ""
