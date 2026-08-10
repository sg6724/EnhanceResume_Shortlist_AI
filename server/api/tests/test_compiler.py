from __future__ import annotations

import httpx
import pytest

from app.agents.compiler import compile_with_retry


class _FakeResponse:
    def __init__(self, status_code: int, json_body: dict | None = None, content: bytes = b""):
        self.status_code = status_code
        self._json_body = json_body or {}
        self.content = content
        self.text = str(json_body)

    def json(self):
        return self._json_body


def _fake_http(responses: list[_FakeResponse]) -> httpx.AsyncClient:
    calls = {"n": 0}

    class _Client:
        async def post(self, *args, **kwargs):
            resp = responses[calls["n"]]
            calls["n"] += 1
            return resp

    return _Client()


def _fake_http_with_error_then_success():
    calls: list[str] = []

    class _Client:
        async def post(self, url, *args, **kwargs):
            calls.append(url)
            if len(calls) == 1:
                raise httpx.ConnectError("Name or service not known")
            return _FakeResponse(200, content=b"%PDF-fallback")

    return _Client(), calls


async def test_retry_continues_after_rewriter_raises_instead_of_aborting():
    """A rewriter failure on one attempt must not burn the remaining retry budget."""
    responses = [
        _FakeResponse(422, {"log": "compile error 1"}),
        _FakeResponse(422, {"log": "compile error 2"}),
        _FakeResponse(200, content=b"%PDF-fake"),
    ]
    http = _fake_http(responses)

    rewriter_calls = {"n": 0}

    async def rewriter_fn(current_tex: str, error_log: str, attempt: int):
        rewriter_calls["n"] += 1
        if rewriter_calls["n"] == 1:
            raise ValueError("LaTeX structure violation")
        return current_tex, "fixed"

    pdf_bytes, final_tex, error_log = await compile_with_retry(
        http=http,
        tex="\\documentclass{article}",
        rewriter_fn=rewriter_fn,
        max_retries=3,
    )

    assert pdf_bytes == b"%PDF-fake"
    assert rewriter_calls["n"] == 2


async def test_all_attempts_exhausted_still_returns_last_error():
    responses = [
        _FakeResponse(422, {"log": "compile error"}),
        _FakeResponse(422, {"log": "compile error"}),
        _FakeResponse(422, {"log": "compile error"}),
    ]
    http = _fake_http(responses)

    async def rewriter_fn(current_tex: str, error_log: str, attempt: int):
        raise ValueError("LaTeX structure violation")

    pdf_bytes, final_tex, error_log = await compile_with_retry(
        http=http,
        tex="\\documentclass{article}",
        rewriter_fn=rewriter_fn,
        max_retries=3,
    )

    assert pdf_bytes is None
    assert "compile error" in error_log


async def test_compile_falls_back_to_public_service_when_configured_url_fails():
    http, calls = _fake_http_with_error_then_success()

    async def rewriter_fn(current_tex: str, error_log: str, attempt: int):
        return current_tex, "fixed"

    pdf_bytes, _final_tex, error_log = await compile_with_retry(
        http=http,
        tex="\\documentclass{article}",
        rewriter_fn=rewriter_fn,
        max_retries=1,
    )

    assert pdf_bytes == b"%PDF-fallback"
    assert error_log == ""
    assert len(calls) == 2
    assert calls[-1] == "https://gethired-compile.onrender.com/compile"
