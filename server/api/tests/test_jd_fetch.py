from __future__ import annotations

from app.agents import jd_fetch

JOBPOSTING_HTML = """
<html><head>
<script type="application/ld+json">
{"@context": "https://schema.org", "@type": "WebPage", "name": "job"}
</script>
<script type="application/ld+json">
{
  "@type": "JobPosting",
  "title": "Backend Engineer",
  "hiringOrganization": {"@type": "Organization", "name": "Acme Labs"},
  "description": "&lt;p&gt;Build &lt;b&gt;APIs&lt;/b&gt; with Python and FastAPI.&lt;/p&gt;",
  "jobLocation": {"address": {"@type": "PostalAddress", "addressLocality": "Bengaluru", "addressRegion": "Karnataka", "addressCountry": "India"}}
}
</script>
</head><body><p>Some rendered page chrome, nav links, cookie banner.</p></body></html>
"""

NO_JOBPOSTING_HTML = """
<html><head><script>var x = 1;</script></head>
<body>
<nav>Site nav</nav>
<div>Acme Labs is hiring a Backend Engineer! We need someone great with Python and FastAPI to join our small team.</div>
<footer>copyright footer</footer>
</body></html>
"""

CLOSED_POSTING_TEXT = "Sorry, the job you are trying to apply for has been filled. Try these other roles."


def test_extract_jsonld_jobposting_finds_the_right_block():
    result = jd_fetch._extract_jsonld_jobposting(JOBPOSTING_HTML)
    assert result is not None
    assert result["title"] == "Backend Engineer"
    assert result["company"] == "Acme Labs"
    assert "APIs" in result["description"]
    assert "<b>" not in result["description"]  # tags stripped
    assert result["location"] == "Bengaluru, Karnataka, India"


def test_extract_jsonld_jobposting_returns_none_when_absent():
    assert jd_fetch._extract_jsonld_jobposting(NO_JOBPOSTING_HTML) is None


def test_extract_jsonld_jobposting_ignores_malformed_json():
    html = '<script type="application/ld+json">{not valid json</script>'
    assert jd_fetch._extract_jsonld_jobposting(html) is None


def test_extract_visible_text_strips_script_nav_footer():
    text = jd_fetch._extract_visible_text(NO_JOBPOSTING_HTML)
    assert "Acme Labs is hiring" in text
    assert "Site nav" not in text
    assert "copyright footer" not in text
    assert "var x = 1" not in text


def test_extract_visible_text_caps_length():
    html = "<html><body>" + ("word " * 2000) + "</body></html>"
    text = jd_fetch._extract_visible_text(html, max_chars=100)
    assert len(text) == 100


def test_detect_closed_posting_true_for_filled():
    assert jd_fetch._detect_closed_posting(CLOSED_POSTING_TEXT) is True


def test_detect_closed_posting_false_for_normal_jd():
    assert jd_fetch._detect_closed_posting(NO_JOBPOSTING_HTML) is False


async def test_llm_extract_jd_parses_json(monkeypatch):
    monkeypatch.setattr(jd_fetch.settings, "gemini_api_key", "k")

    async def fake_generate(prompt, *, gemini_model, groq_model):
        return '{"company": "Scalant Labs", "title": "Backend Intern", "jd_text": "Build APIs."}'

    monkeypatch.setattr(jd_fetch, "generate", fake_generate)

    result = await jd_fetch._llm_extract_jd("some scraped page text")
    assert result == {"company": "Scalant Labs", "title": "Backend Intern", "jd_text": "Build APIs."}


async def test_llm_extract_jd_returns_empty_on_generate_error(monkeypatch):
    monkeypatch.setattr(jd_fetch.settings, "gemini_api_key", "k")

    async def fake_generate(prompt, *, gemini_model, groq_model):
        raise RuntimeError("no LLM provider available")

    monkeypatch.setattr(jd_fetch, "generate", fake_generate)

    result = await jd_fetch._llm_extract_jd("some scraped page text")
    assert result == {"company": "", "title": "", "jd_text": ""}


async def test_llm_extract_jd_short_circuits_with_no_keys(monkeypatch):
    monkeypatch.setattr(jd_fetch.settings, "gemini_api_key", "")
    monkeypatch.setattr(jd_fetch.settings, "groq_api_key", "")

    result = await jd_fetch._llm_extract_jd("some scraped page text")
    assert result == {"company": "", "title": "", "jd_text": ""}


async def test_fetch_jd_from_url_uses_jsonld_path(monkeypatch):
    class FakeResponse:
        status_code = 200
        text = JOBPOSTING_HTML

    class FakeHttp:
        async def get(self, url, **kwargs):
            return FakeResponse()

    result = await jd_fetch.fetch_jd_from_url(FakeHttp(), "https://example.com/job/1")
    assert result["source"] == "jsonld"
    assert result["company"] == "Acme Labs"
    assert result["title"] == "Backend Engineer"
    assert "APIs" in result["jd_text"]
    assert result["possibly_closed"] is False


async def test_fetch_jd_from_url_detects_closure_from_stale_jsonld_page():
    """JSON-LD metadata can be stale — a closed posting's JobPosting block
    still describes the original opening, but the live page chrome shows
    a 'this job has been filled' banner. possibly_closed must catch this
    even though the closure text never appears inside the description
    field itself (regression test for a real GE HealthCare career page)."""
    html = JOBPOSTING_HTML.replace(
        "<p>Some rendered page chrome, nav links, cookie banner.</p>",
        "<p>Sorry, the job you are trying to apply for has been filled.</p>",
    )

    class FakeResponse:
        status_code = 200
        text = html

    class FakeHttp:
        async def get(self, url, **kwargs):
            return FakeResponse()

    result = await jd_fetch.fetch_jd_from_url(FakeHttp(), "https://example.com/job/1")
    assert result["source"] == "jsonld"
    assert result["possibly_closed"] is True


async def test_fetch_jd_from_url_falls_back_to_llm(monkeypatch):
    class FakeResponse:
        status_code = 200
        text = NO_JOBPOSTING_HTML

    class FakeHttp:
        async def get(self, url, **kwargs):
            return FakeResponse()

    async def fake_generate(prompt, *, gemini_model, groq_model):
        return '{"company": "Acme Labs", "title": "Backend Engineer", "jd_text": "Python and FastAPI role."}'

    monkeypatch.setattr(jd_fetch.settings, "gemini_api_key", "k")
    monkeypatch.setattr(jd_fetch, "generate", fake_generate)

    result = await jd_fetch.fetch_jd_from_url(FakeHttp(), "https://example.com/job/2")
    assert result["source"] == "llm_extracted"
    assert result["company"] == "Acme Labs"
    assert "FastAPI" in result["jd_text"]


async def test_fetch_jd_from_url_reports_non_200():
    class FakeResponse:
        status_code = 404
        text = ""

    class FakeHttp:
        async def get(self, url, **kwargs):
            return FakeResponse()

    result = await jd_fetch.fetch_jd_from_url(FakeHttp(), "https://example.com/gone")
    assert "error" in result
    assert "404" in result["error"]


async def test_fetch_jd_from_url_reports_connection_error():
    class FakeHttp:
        async def get(self, url, **kwargs):
            raise ConnectionError("boom")

    result = await jd_fetch.fetch_jd_from_url(FakeHttp(), "https://unreachable.example")
    assert "error" in result
