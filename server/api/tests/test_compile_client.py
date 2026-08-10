from __future__ import annotations

import httpx

from app.compile_client import compile_tex


def _fake_http_with_error_then_success():
    calls: list[str] = []

    class _Client:
        async def post(self, url, *args, **kwargs):
            calls.append(url)
            if len(calls) == 1:
                raise httpx.ConnectError("Name or service not known")
            return httpx.Response(200, content=b"%PDF-fallback")

    return _Client(), calls


async def test_compile_tex_falls_back_to_public_service_when_configured_url_fails():
    http, calls = _fake_http_with_error_then_success()

    resp = await compile_tex(http=http, tex="\\documentclass{article}")

    assert resp.status_code == 200
    assert resp.content == b"%PDF-fallback"
    assert len(calls) == 2
    assert calls[-1] == "https://gethired-compile.onrender.com/compile"
