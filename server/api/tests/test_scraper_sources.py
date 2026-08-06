from __future__ import annotations

from app.agents import scraper


async def test_explicit_source_urls_skip_job_board_fallbacks(monkeypatch):
    calls = {"remoteok": 0, "adzuna": 0, "apify": 0}

    async def fake_remoteok(keywords):
        calls["remoteok"] += 1
        return []

    async def fake_adzuna(keywords):
        calls["adzuna"] += 1
        return []

    async def fake_apify(http, keywords, *, career_urls=None, linkedin_urls=None, x_urls=None):
        calls["apify"] += 1
        assert career_urls == ["https://www.amazon.jobs/"]
        return [{
            "source": "career_page",
            "company": "Amazon",
            "title": "Applied Scientist",
            "location": "Remote",
            "url": "https://www.amazon.jobs/job/123",
            "raw_text": "Applied Scientist at Amazon\n\n" + "machine learning " * 20,
        }]

    monkeypatch.setattr(scraper, "_fetch_remoteok", fake_remoteok)
    monkeypatch.setattr(scraper, "_fetch_adzuna", fake_adzuna)
    monkeypatch.setattr(scraper, "fetch_apify_jobs", fake_apify)

    jobs = await scraper.scrape_jds(
        ["AI Engineer"],
        http=object(),
        career_urls=["https://www.amazon.jobs/"],
    )

    assert calls == {"remoteok": 0, "adzuna": 0, "apify": 1}
    assert jobs[0]["company"] == "Amazon"


async def test_default_scrape_uses_job_boards_when_no_explicit_sources(monkeypatch):
    calls = {"remoteok": 0, "adzuna": 0, "apify": 0}

    async def fake_remoteok(keywords):
        calls["remoteok"] += 1
        return []

    async def fake_adzuna(keywords):
        calls["adzuna"] += 1
        return []

    async def fake_apify(http, keywords, *, career_urls=None, linkedin_urls=None, x_urls=None):
        calls["apify"] += 1
        return []

    monkeypatch.setattr(scraper, "_fetch_remoteok", fake_remoteok)
    monkeypatch.setattr(scraper, "_fetch_adzuna", fake_adzuna)
    monkeypatch.setattr(scraper, "fetch_apify_jobs", fake_apify)

    await scraper.scrape_jds(["AI Engineer"], http=object())

    assert calls == {"remoteok": 1, "adzuna": 1, "apify": 1}
