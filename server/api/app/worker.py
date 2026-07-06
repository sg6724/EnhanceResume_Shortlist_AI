"""Entry point: cd server/api && uv run python -m app.worker"""
from __future__ import annotations

import asyncio

from .queue import proc_app


async def main() -> None:
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


if __name__ == "__main__":
    asyncio.run(main())
