from __future__ import annotations

from typing import Callable, Awaitable

import httpx

from ..config import settings
from ..services.email import notify_compile_failed


async def compile_with_retry(
    http: httpx.AsyncClient,
    tex: str,
    rewriter_fn: Callable[[str, str, int], Awaitable[tuple[str, str]]],
    max_retries: int = 3,
    jd_info: dict | None = None,
) -> tuple[bytes | None, str, str]:
    """
    Attempt to compile tex via the compile service.
    On failure, calls rewriter_fn(current_tex, error_log, attempt) to get a corrected tex.
    Returns (pdf_bytes_or_None, final_tex, error_log).
    """
    current_tex = tex
    last_error = ""

    for attempt in range(1, max_retries + 1):
        try:
            resp = await http.post(
                f"{settings.compile_service_url}/compile",
                json={"tex": current_tex, "engine": "pdflatex", "jobname": "resume"},
                timeout=150.0,
            )
        except Exception as e:
            last_error = f"HTTP error calling compile service: {e}"
            break

        if resp.status_code == 200:
            return resp.content, current_tex, ""

        last_error = resp.json().get("log", resp.text)[:2000]
        print(f"[compiler] Attempt {attempt}/{max_retries} failed")

        if attempt < max_retries:
            try:
                current_tex, _ = await rewriter_fn(current_tex, last_error, attempt)
            except Exception as e:
                last_error = f"Rewriter error on attempt {attempt}: {e}"
                break

    # All attempts failed
    if jd_info:
        notify_compile_failed(
            settings.user_email,
            jd_info.get("company", "Unknown"),
            jd_info.get("title", "Unknown"),
        )
    return None, current_tex, last_error
