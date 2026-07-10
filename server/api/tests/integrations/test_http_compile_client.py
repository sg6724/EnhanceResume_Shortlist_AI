import httpx

from app.integrations.compile.http import HttpCompileClient


async def test_compile_success_returns_pdf_bytes():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"%PDF-1.4 fake pdf")

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = HttpCompileClient(http=http, service_url="http://localhost:8001")
    result = await client.compile("\\documentclass{article}")
    await http.aclose()

    assert result.success is True
    assert result.pdf_bytes == b"%PDF-1.4 fake pdf"
    assert result.error_log == ""


async def test_compile_failure_returns_error_log_from_json():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"log": "! Undefined control sequence."})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = HttpCompileClient(http=http, service_url="http://localhost:8001")
    result = await client.compile("\\documentclass{article}\\badcommand")
    await http.aclose()

    assert result.success is False
    assert result.pdf_bytes is None
    assert "Undefined control sequence" in result.error_log


async def test_compile_handles_connection_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = HttpCompileClient(http=http, service_url="http://localhost:8001")
    result = await client.compile("\\documentclass{article}")
    await http.aclose()

    assert result.success is False
    assert "connection refused" in result.error_log.lower() or "connecterror" in result.error_log.lower()
