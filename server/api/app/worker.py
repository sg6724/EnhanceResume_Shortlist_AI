"""Entry point: cd server/api && uv run python -m app.worker"""
from __future__ import annotations

import asyncio
import sys

# Force UTF-8 stdout/stderr so pipeline prints containing non-ASCII (e.g. "→")
# don't crash on Windows' default cp1252 console encoding. line_buffering=True
# flushes each line immediately so pipeline progress is visible in real time
# (otherwise prints sit in the block buffer until the process exits).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

# psycopg3 requires SelectorEventLoop on Windows (not ProactorEventLoop). This
# entry point doesn't import app.main, so set the policy here before asyncio.run
# creates the loop — otherwise the Procrastinate psycopg pool can't connect.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from procrastinate.exceptions import ConnectorException

from .queue import proc_app


async def _run_once() -> None:
    async with proc_app.open_async():
        print("[worker] Procrastinate worker started. Listening for jobs...")
        await proc_app.run_worker_async(
            queues=["default"],
            install_signal_handlers=True,
            # LISTEN/NOTIFY needs a persistent session connection, which the
            # transaction-mode pooler (required for IPv4 connectivity) doesn't
            # support. Fall back to polling.
            listen_notify=False,
        )


async def main() -> None:
    """Supervise the worker: a transient DB/DNS blip (Supabase's pooler drops idle
    connections, and getaddrinfo can momentarily fail) surfaces as a
    ConnectorException/OSError that would otherwise kill the whole process. Restart
    the worker after a short backoff so it stays up across such blips."""
    backoff = 3
    while True:
        try:
            await _run_once()
            return  # clean shutdown (e.g. signal) — don't restart
        except (ConnectorException, OSError) as e:
            print(f"[worker] transient DB/connection error: {e!r} — restarting in {backoff}s")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
        else:
            backoff = 3


if __name__ == "__main__":
    asyncio.run(main())
