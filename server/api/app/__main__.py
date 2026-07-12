"""Local-dev entrypoint: `cd server/api && uv run python -m app`

On Windows, uvicorn's CLI creates a ProactorEventLoop before importing the app,
which psycopg (used by the Procrastinate queue) cannot run in async mode. Setting
the SelectorEventLoop policy *here*, before uvicorn creates its loop, avoids that.
The Docker image still launches via the uvicorn CLI (Linux uses a selector loop
by default, so this shim isn't needed there).
"""
from __future__ import annotations

import asyncio
import os
import sys

# Force UTF-8 stdout/stderr so logs/prints with non-ASCII don't crash on
# Windows' default cp1252 console encoding.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("API_RELOAD") == "1",
    )
