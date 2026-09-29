from __future__ import annotations

import httpx
import pytest

from app.routers import copies
from tests.fakes import FakeSupabase


class _State:
    def __init__(self, sb, http):
        self.supabase = sb
        self.http = http


class _App:
    def __init__(self, sb, http):
        self.state = _State(sb, http)


class _Request:
    def __init__(self, sb, http):
        self.app = _App(sb, http)


def _seed() -> FakeSupabase:
    sb = FakeSupabase()
    sb.tables["resume_copies"] = [
        {"id": "c1", "user_id": "u1", "status": "failed", "tex_content": "old"}
    ]
    return sb


def _http_returning(resp: httpx.Response):
    class _Client:
        async def post(self, *args, **kwargs):
            return resp

    return _Client()


async def test_update_tex_survives_non_json_compile_error_body():
    """Render's proxy answers a cold compile service with an HTML 502. That must come
    back as a normal {"status": "failed"} payload (so CORS headers are attached and the
    UI can show it), not an unhandled 500 that the browser reports as "Failed to fetch"."""
    sb = _seed()
    http = _http_returning(httpx.Response(502, text="<html>Bad Gateway</html>"))

    out = await copies.update_tex("c1", copies.TexUpdateIn(tex_content="new"), _Request(sb, http))

    assert out["status"] == "failed"
    assert "502" in out["log"] or "Bad Gateway" in out["log"]
    assert sb.tables["resume_copies"][0]["status"] == "failed"


async def test_update_tex_never_leaves_row_stuck_in_compiling_on_unexpected_error(monkeypatch):
    sb = _seed()

    async def _boom(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr(copies, "compile_tex", _boom)

    out = await copies.update_tex("c1", copies.TexUpdateIn(tex_content="new"), _Request(sb, None))

    assert out["status"] == "failed"
    assert sb.tables["resume_copies"][0]["status"] == "failed"
    assert sb.tables["resume_copies"][0]["tex_content"] == "new"
