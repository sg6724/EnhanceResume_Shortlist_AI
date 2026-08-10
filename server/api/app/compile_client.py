from __future__ import annotations

import httpx

from .config import settings

PUBLIC_COMPILE_SERVICE_URL = "https://gethired-compile.onrender.com"


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
            return await http.post(
                f"{service_url}/compile",
                json={"tex": tex, "engine": engine, "jobname": jobname},
            )
        except Exception as e:
            last_error = f"HTTP error calling compile service at {service_url}: {e}"
            continue
    return httpx.Response(
        status_code=503,
        json={"detail": "compile service unavailable", "log": last_error},
    )
