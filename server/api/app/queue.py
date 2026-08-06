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
    # Supabase's transaction-mode pooler (port 6543) multiplexes many client
    # sessions onto shared server connections, so server-side prepared statements
    # collide across transactions ("prepared statement _pg3_0 already exists").
    # Disable psycopg3's auto-prepare so it uses the simple/extended protocol
    # without naming statements. `kwargs` is forwarded to each pool connection's
    # psycopg.connect().
    # Keep the pool small: Supabase's pooler caps concurrent client connections,
    # and BOTH the API and the worker open their own pool. A large default
    # (min_size=4 each) can exhaust the cap and make pool init time out.
    return PsycopgConnector(
        conninfo=dsn,
        kwargs={"prepare_threshold": None},
        min_size=1,
        max_size=4,
    )


proc_app = App(
    connector=_make_connector(),
    import_paths=["app.queue"],
)


@proc_app.task(name="scrape_and_process", queue="default", retry=3)
async def scrape_and_process_task(
    user_id: str,
    career_urls: list[str] | None = None,
    linkedin_urls: list[str] | None = None,
    x_urls: list[str] | None = None,
) -> None:
    import httpx
    from supabase import acreate_client
    from .agents.orchestrator import run_pipeline

    sb = await acreate_client(settings.supabase_url, settings.supabase_service_key)
    http = httpx.AsyncClient(timeout=130.0)
    try:
        result = await run_pipeline(
            user_id,
            sb,
            http,
            career_urls=career_urls,
            linkedin_urls=linkedin_urls,
            x_urls=x_urls,
        )
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


@proc_app.task(name="run_manual_match", queue="default", retry=1)
async def run_manual_match_task(jd_id: str) -> None:
    import httpx
    from supabase import acreate_client
    from .agents.orchestrator import run_manual_match

    sb = await acreate_client(settings.supabase_url, settings.supabase_service_key)
    http = httpx.AsyncClient(timeout=150.0)
    try:
        result = await run_manual_match(jd_id, sb, http)
        print(f"[task:manual_match] {result}")
    finally:
        await http.aclose()


@proc_app.task(name="prepare_application", queue="default", retry=1)
async def prepare_application_task(
    run_id: str,
    user_id: str,
    career_urls: list[str] | None = None,
    linkedin_urls: list[str] | None = None,
    x_urls: list[str] | None = None,
) -> None:
    import httpx
    from supabase import acreate_client
    from .agents.application_prep import run_application_prep

    sb = await acreate_client(settings.supabase_url, settings.supabase_service_key)
    http = httpx.AsyncClient(timeout=280.0)
    try:
        result = await run_application_prep(
            run_id, user_id, sb, http,
            career_urls=career_urls or [], linkedin_urls=linkedin_urls or [], x_urls=x_urls or [],
        )
        print(f"[task:prepare_application] {result}")
    finally:
        await http.aclose()


@proc_app.task(name="retry_application_target", queue="default", retry=1)
async def retry_application_target_task(target_id: str) -> None:
    import httpx
    from supabase import acreate_client
    from .agents.application_prep import retry_target

    sb = await acreate_client(settings.supabase_url, settings.supabase_service_key)
    http = httpx.AsyncClient(timeout=150.0)
    try:
        result = await retry_target(target_id, sb, http)
        print(f"[task:retry_target] {result}")
    finally:
        await http.aclose()

