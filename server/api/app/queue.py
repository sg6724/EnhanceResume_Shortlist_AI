from __future__ import annotations

from procrastinate import App, PsycopgConnector

from .config import settings


def _make_connector() -> PsycopgConnector:
    db_url = settings.database_url
    # Return a bare connector (no conninfo) when DATABASE_URL is unset or still a placeholder
    if not db_url or "[YOUR-PASSWORD]" in db_url:
        return PsycopgConnector()
    # Strip SQLAlchemy dialect prefix; psycopg needs plain postgresql://
    dsn = db_url.replace("postgresql+asyncpg://", "postgresql://")
    return PsycopgConnector(conninfo=dsn)


proc_app = App(
    connector=_make_connector(),
    import_paths=["app.queue"],
)


@proc_app.task(name="scrape_and_process", queue="default", retry=3)
async def scrape_and_process_task(user_id: str) -> None:
    import httpx
    from supabase import acreate_client
    from .agents.orchestrator import run_pipeline

    sb = await acreate_client(settings.supabase_url, settings.supabase_service_key)
    http = httpx.AsyncClient(timeout=130.0)
    try:
        result = await run_pipeline(user_id, sb, http)
        print(f"[task:scrape] {result}")
    finally:
        await http.aclose()


@proc_app.task(name="rewrite_resume", queue="default", retry=1)
async def rewrite_resume_task(checkpoint_id: str) -> None:
    import httpx
    from supabase import acreate_client
    from .agents.orchestrator import run_rewrite

    sb = await acreate_client(settings.supabase_url, settings.supabase_service_key)
    http = httpx.AsyncClient(timeout=150.0)
    try:
        result = await run_rewrite(checkpoint_id, sb, http)
        print(f"[task:rewrite] {result}")
    finally:
        await http.aclose()
