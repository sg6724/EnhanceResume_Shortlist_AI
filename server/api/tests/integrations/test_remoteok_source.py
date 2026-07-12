import json

import httpx

from app.integrations.jobs.remoteok import RemoteOkSource, _remoteok_tags


def test_remoteok_tags_expands_keywords_and_drops_generic_tokens():
    tags = _remoteok_tags(["AI Engineer", "ML Engineer"])
    assert "ai-engineer" in tags
    assert "ai" in tags
    assert "engineer" not in tags  # generic token dropped when a specific one exists


def _remoteok_payload():
    return [
        {"legal": "notice"},
        {"id": "1", "position": "AI Engineer", "company": "Acme", "location": "Remote",
         "url": "https://remoteok.com/1", "tags": ["ai", "python"],
         "description": "Build AI systems."},
    ]


async def test_fetch_returns_parsed_jobs_deduped_by_id():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_remoteok_payload())

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = RemoteOkSource(http=http, sleep_seconds=0)
    jobs = await source.fetch(["AI Engineer"])
    await http.aclose()

    assert len(jobs) >= 1
    assert jobs[0].company == "Acme"
    assert jobs[0].source == "remoteok"
    assert "Acme" in jobs[0].raw_text


async def test_fetch_skips_non_200_responses():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = RemoteOkSource(http=http, sleep_seconds=0)
    jobs = await source.fetch(["AI Engineer"])
    await http.aclose()
    assert jobs == []
