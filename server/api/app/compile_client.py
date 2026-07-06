from __future__ import annotations

import httpx

from .config import settings


async def compile_tex(
    http: httpx.AsyncClient,
    tex: str,
    engine: str = "pdflatex",
    jobname: str = "resume",
) -> httpx.Response:
    return await http.post(
        f"{settings.compile_service_url}/compile",
        json={"tex": tex, "engine": engine, "jobname": jobname},
    )
