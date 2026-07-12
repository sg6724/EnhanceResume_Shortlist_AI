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


@proc_app.task(name="run_outreach", queue="default", retry=1)
async def run_outreach_task(user_id: str) -> None:
    import httpx
    from supabase import acreate_client
    from .agents.outreach_orchestrator import run_outreach_cycle

    sb = await acreate_client(settings.supabase_url, settings.supabase_service_key)
    http = httpx.AsyncClient(timeout=60.0)
    try:
        result = await run_outreach_cycle(user_id, sb, http)
        print(f"[task:outreach] {result}")
    finally:
        await http.aclose()


@proc_app.task(name="send_outreach_email", queue="default", retry=1)
async def send_outreach_email_task(draft_id: str) -> None:
    import httpx
    from supabase import acreate_client
    from .agents.outreach_orchestrator import send_outreach

    sb = await acreate_client(settings.supabase_url, settings.supabase_service_key)
    http = httpx.AsyncClient(timeout=130.0)
    try:
        result = await send_outreach(draft_id, sb, http)
        print(f"[task:outreach_send] {result}")
    finally:
        await http.aclose()


@proc_app.periodic(cron="0 * * * *")
@proc_app.task(name="outreach_tick", queue="default")
async def outreach_tick(timestamp: int) -> None:
    """Hourly tick: run an outreach cycle for each user whose interval elapsed."""
    from datetime import datetime, timedelta, timezone
    from supabase import acreate_client

    sb = await acreate_client(settings.supabase_url, settings.supabase_service_key)
    # Single-user app: settings.user_email identifies the one active account.
    # Older/stale rows can linger in `users` (e.g. after the configured email
    # changed) — without this filter, every row got an hourly outreach cycle
    # queued against it forever, burning Hunter quota on dead accounts.
    users = await sb.table("users").select(
        "id, outreach_enabled, outreach_interval_hours, outreach_last_run_at"
    ).eq("email", settings.user_email).execute()
    now = datetime.now(timezone.utc)
    for u in users.data:
        if not u.get("outreach_enabled", True):
            continue
        last = u.get("outreach_last_run_at")
        if last:
            last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            if now - last_dt < timedelta(hours=u.get("outreach_interval_hours", 24)):
                continue
        await run_outreach_task.defer_async(user_id=u["id"])
        print(f"[tick:outreach] queued cycle for {u['id']}")
