import httpx

from app.integrations.jobs.adzuna import AdzunaSource


async def test_fetch_returns_empty_when_no_credentials():
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"results": []})))
    source = AdzunaSource(http=http, app_id="", api_key="")
    jobs = await source.fetch(["AI Engineer"])
    await http.aclose()
    assert jobs == []


async def test_fetch_parses_results_when_credentials_present():
    payload = {"results": [{
        "title": "AI Engineer", "company": {"display_name": "Acme"},
        "location": {"display_name": "Remote"}, "redirect_url": "https://x",
        "description": "Build AI systems.",
    }]}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = AdzunaSource(http=http, app_id="id", api_key="key")
    jobs = await source.fetch(["AI Engineer"])
    await http.aclose()

    assert len(jobs) == 1
    assert jobs[0].company == "Acme"
    assert jobs[0].source == "adzuna"


async def test_fetch_handles_non_200_gracefully():
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    source = AdzunaSource(http=http, app_id="id", api_key="key")
    jobs = await source.fetch(["AI Engineer"])
    await http.aclose()
    assert jobs == []
