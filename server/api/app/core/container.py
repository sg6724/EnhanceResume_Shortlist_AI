from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from ..data.repositories.checkpoints_repo import CheckpointsRepo
from ..data.repositories.copies_repo import CopiesRepo
from ..data.repositories.jds_repo import JdsRepo
from ..data.repositories.matches_repo import MatchesRepo
from ..data.repositories.outreach_repo import OutreachDraftsRepo, OutreachTargetsRepo
from ..data.repositories.positions_repo import PositionsRepo
from ..data.repositories.quota_repo import QuotaRepo
from ..data.repositories.resume_repo import ResumeRepo
from ..data.repositories.traces_repo import TracesRepo
from ..data.repositories.users_repo import UsersRepo
from ..integrations.compile.base import CompileClient
from ..integrations.compile.http import HttpCompileClient
from ..integrations.contacts.base import ContactProvider
from ..integrations.contacts.sitescrape import SiteScrapeProvider
from ..integrations.email.base import EmailSender
from ..integrations.email.resend import ResendSender
from ..integrations.jobs.adzuna import AdzunaSource
from ..integrations.jobs.base import JobSource
from ..integrations.jobs.remoteok import RemoteOkSource
from ..integrations.llm.base import LlmClient
from ..integrations.llm.gemini import GeminiClient
from .config import Settings


@dataclass
class Container:
    settings: Settings
    sb: Any
    http: httpx.AsyncClient

    positions: PositionsRepo
    users: UsersRepo
    jds: JdsRepo
    matches: MatchesRepo
    checkpoints: CheckpointsRepo
    copies: CopiesRepo
    resume: ResumeRepo
    outreach_targets: OutreachTargetsRepo
    outreach_drafts: OutreachDraftsRepo
    traces: TracesRepo
    quota: QuotaRepo

    llm: LlmClient
    email: EmailSender
    compile: CompileClient
    job_sources: list[JobSource] = field(default_factory=list)
    contact_providers: list[ContactProvider] = field(default_factory=list)


def build_container(settings: Settings, sb: Any, http: httpx.AsyncClient) -> Container:
    """Synchronous composition root. `sb` and `http` are already-constructed
    clients (async construction happens in the app lifespan); this function
    only builds cheap, I/O-free objects, so it is safe to call from tests
    without touching the network."""
    llm = GeminiClient(api_key=settings.llm.gemini_api_key)
    email = ResendSender(api_key=settings.email.resend_api_key, from_addr=settings.email.resend_from)
    compile_client = HttpCompileClient(http=http, service_url=settings.compile.compile_service_url)

    job_sources: list = [
        RemoteOkSource(http=http),
        AdzunaSource(http=http, app_id=settings.contacts.adzuna_app_id, api_key=settings.contacts.adzuna_api_key),
    ]
    contact_providers: list = [SiteScrapeProvider(http=http, llm=llm)]

    return Container(
        settings=settings,
        sb=sb,
        http=http,
        positions=PositionsRepo(sb),
        users=UsersRepo(sb),
        jds=JdsRepo(sb),
        matches=MatchesRepo(sb),
        checkpoints=CheckpointsRepo(sb),
        copies=CopiesRepo(sb),
        resume=ResumeRepo(sb),
        outreach_targets=OutreachTargetsRepo(sb),
        outreach_drafts=OutreachDraftsRepo(sb),
        traces=TracesRepo(sb),
        quota=QuotaRepo(sb),
        llm=llm,
        email=email,
        compile=compile_client,
        job_sources=job_sources,
        contact_providers=contact_providers,
    )
