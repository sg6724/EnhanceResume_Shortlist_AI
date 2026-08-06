from __future__ import annotations

import asyncio
import sys

# psycopg3 requires SelectorEventLoop on Windows (not ProactorEventLoop)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import AsyncClient, acreate_client

from .config import settings
from .core.container import build_container
from .routers import compile as compile_router
from .routers import (
    health,
    master_resume,
    positions,
    jobs,
    matches,
    copies,
    checkpoints,
    traces,
    outreach,
    quick_match,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.supabase: AsyncClient = await acreate_client(
        settings.supabase_url,
        settings.supabase_service_key,
    )
    app.state.http = httpx.AsyncClient(timeout=130.0)
    app.state.container = build_container(settings, app.state.supabase, app.state.http)

    # Open Procrastinate only when DATABASE_URL is a real configured value
    if settings.database_url and "[YOUR-PASSWORD]" not in settings.database_url:
        from .queue import proc_app
        async with proc_app.open_async():
            try:
                yield
            finally:
                await app.state.http.aclose()
    else:
        try:
            yield
        finally:
            await app.state.http.aclose()


app = FastAPI(title="job-hunt-api", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(compile_router.router)
app.include_router(master_resume.router)
app.include_router(positions.router)
app.include_router(jobs.router)
app.include_router(matches.router)
app.include_router(copies.router)
app.include_router(checkpoints.router)
app.include_router(traces.router)
app.include_router(outreach.router)
app.include_router(quick_match.router)
