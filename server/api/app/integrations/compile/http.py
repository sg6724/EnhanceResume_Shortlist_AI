from __future__ import annotations

import httpx

from ...domain.models import CompileResult


class HttpCompileClient:
    """POSTs tex to the standalone compile microservice and returns the PDF
    bytes or the compiler error log — never raises."""

    def __init__(self, http: httpx.AsyncClient, service_url: str):
        self._http = http
        self._service_url = service_url

    async def compile(self, tex: str, engine: str = "pdflatex", jobname: str = "resume") -> CompileResult:
        try:
            resp = await self._http.post(
                f"{self._service_url}/compile",
                json={"tex": tex, "engine": engine, "jobname": jobname},
                timeout=150.0,
            )
        except Exception as e:
            return CompileResult(success=False, error_log=f"HTTP error calling compile service: {e!r}")

        if resp.status_code == 200:
            return CompileResult(success=True, pdf_bytes=resp.content)

        try:
            log = resp.json().get("log", resp.text)
        except Exception:
            log = resp.text
        return CompileResult(success=False, error_log=log[:2000])
