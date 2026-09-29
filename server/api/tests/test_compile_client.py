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


def _client_returning(statuses: list[int]):
    calls: list[str] = []

    class _Client:
        async def post(self, url, *args, **kwargs):
            calls.append(url)
            code = statuses[min(len(calls) - 1, len(statuses) - 1)]
            if code == 200:
                return httpx.Response(200, content=b"%PDF-ok")
            return httpx.Response(code, text="Too Many Requests")

    return _Client(), calls


async def test_compile_tex_retries_transient_429_then_succeeds(monkeypatch):
    from app import compile_client

    async def _no_sleep(_s):
        pass

    monkeypatch.setattr(compile_client, "_sleep", _no_sleep)
    http, calls = _client_returning([429, 429, 200])

    resp = await compile_tex(http=http, tex="x")

    assert resp.status_code == 200
    assert len(calls) == 3


async def test_compile_tex_gives_up_after_bounded_retries(monkeypatch):
    from app import compile_client

    async def _no_sleep(_s):
        pass

    monkeypatch.setattr(compile_client, "_sleep", _no_sleep)
    http, calls = _client_returning([429])

    resp = await compile_tex(http=http, tex="x")

    assert resp.status_code == 429
    assert len(calls) == compile_client.MAX_ATTEMPTS


async def test_compile_tex_does_not_retry_real_compile_errors(monkeypatch):
    from app import compile_client

    async def _no_sleep(_s):
        pass

    monkeypatch.setattr(compile_client, "_sleep", _no_sleep)
    http, calls = _client_returning([422])

    resp = await compile_tex(http=http, tex="x")

    assert resp.status_code == 422
    assert len(calls) == 1
