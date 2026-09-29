from __future__ import annotations

import asyncio

import httpx

from .config import settings

PUBLIC_COMPILE_SERVICE_URL = "https://gethired-compile.onrender.com"

# Render's free tier answers 429/502/503/504 while the compile service is cold-starting
# or briefly saturated. Those are transient, unlike a real LaTeX error (422).
TRANSIENT_STATUSES = {429, 502, 503, 504}
MAX_ATTEMPTS = 4
_BACKOFF_SECONDS = (3.0, 8.0, 15.0)


async def _sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


async def post_compile(
    http: httpx.AsyncClient, service_url: str, payload: dict, timeout: float | None = None
) -> httpx.Response:
    """POST to one compile service, retrying transient proxy errors with backoff."""
    kwargs = {"json": payload}
    if timeout is not None:
        kwargs["timeout"] = timeout
    resp = await http.post(f"{service_url}/compile", **kwargs)
    for delay in _BACKOFF_SECONDS[: MAX_ATTEMPTS - 1]:
        if resp.status_code not in TRANSIENT_STATUSES:
            break
        await _sleep(delay)
        resp = await http.post(f"{service_url}/compile", **kwargs)
    return resp


def _compile_service_urls() -> list[str]:
    urls = [settings.compile.compile_service_url.rstrip("/")]
    if PUBLIC_COMPILE_SERVICE_URL not in urls:
        urls.append(PUBLIC_COMPILE_SERVICE_URL)
    return urls


async def compile_tex(
    http: httpx.AsyncClient,
    tex: str,
    engine: str = "pdflatex",
    jobname: str = "resume",
) -> httpx.Response:
    last_error = ""
    for service_url in _compile_service_urls():
        try:
            return await post_compile(
                http, service_url, {"tex": tex, "engine": engine, "jobname": jobname}
            )
        except Exception as e:
            last_error = f"HTTP error calling compile service at {service_url}: {e}"
            continue
    return httpx.Response(
        status_code=503,
        json={"detail": "compile service unavailable", "log": last_error},
    )


def compile_error_log(resp: httpx.Response, limit: int = 2000) -> str:
    """Best-effort error text from a non-200 compile response. The compile service
    returns {"log": ...}, but a proxy in front of it (e.g. Render while the free
    instance cold-starts) answers with HTML, so never assume the body is JSON."""
    try:
        body = resp.json()
        log = body.get("log") if isinstance(body, dict) else None
    except Exception:
        log = None
    return (log or f"compile service returned HTTP {resp.status_code}: {resp.text}")[:limit]
