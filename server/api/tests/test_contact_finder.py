from app.agents import contact_finder
from app.agents.contact_finder import guess_emails, candidate_domains, _domain_page_matches


def test_guess_emails_patterns():
    assert guess_emails("Ada", "Ng", "x.io") == ["ada@x.io", "ada.ng@x.io", "ang@x.io"]


def test_guess_emails_handles_missing_last():
    assert guess_emails("Ada", "", "x.io") == ["ada@x.io"]


def test_candidate_domains_normalizes():
    assert candidate_domains("Acme Labs, Inc.") == ["acmelabs.com", "acmelabs.io", "acmelabs.ai"]


def test_candidate_domains_strips_suffixes():
    for name in ["Acme Inc", "Acme LLC", "Acme Ltd.", "Acme Technologies Pvt Ltd"]:
        assert candidate_domains(name)[0].startswith("acme"), name


def test_domain_page_matches_rejects_short_tokens():
    # Short slugs like "zip", "ai", "co" are common startup names but also
    # common English substrings; never accept a match for them even if the
    # title contains the token.
    assert _domain_page_matches("zip", "Zip - Fast Checkout", "zip checkout") is False
    assert _domain_page_matches("co", "Company homepage", "co co co") is False


def test_domain_page_matches_accepts_long_token_in_title():
    assert _domain_page_matches("acmelabs", "Acme Labs | Home", "welcome") is True


def test_domain_page_matches_rejects_long_token_only_in_body():
    # Token coincidentally present in the body text but absent from the
    # title should not be accepted - title match is the stronger signal.
    assert _domain_page_matches("acmelabs", "Contact Us", "visit acmelabs somewhere in copy") is False


def test_domain_page_matches_rejects_missing_title():
    assert _domain_page_matches("acmelabs", None, "acmelabs acmelabs acmelabs") is False


async def test_extract_leaders_parses_json(monkeypatch):
    monkeypatch.setattr(contact_finder.settings, "gemini_api_key", "k")

    async def fake_generate(prompt, *, gemini_model, groq_model):
        return '{"people": [{"name": "Ada Ng", "title": "CTO"}]}'

    monkeypatch.setattr(contact_finder, "generate", fake_generate)

    leaders = await contact_finder._extract_leaders("some team page text", "Acme")
    assert leaders == [{"name": "Ada Ng", "title": "CTO"}]


async def test_extract_leaders_returns_empty_on_generate_error(monkeypatch):
    monkeypatch.setattr(contact_finder.settings, "gemini_api_key", "k")

    async def fake_generate(prompt, *, gemini_model, groq_model):
        raise RuntimeError("no LLM provider available")

    monkeypatch.setattr(contact_finder, "generate", fake_generate)

    leaders = await contact_finder._extract_leaders("some team page text", "Acme")
    assert leaders == []


async def test_extract_leaders_short_circuits_with_no_keys(monkeypatch):
    monkeypatch.setattr(contact_finder.settings, "gemini_api_key", "")
    monkeypatch.setattr(contact_finder.settings, "groq_api_key", "")

    leaders = await contact_finder._extract_leaders("some team page text", "Acme")
    assert leaders == []
