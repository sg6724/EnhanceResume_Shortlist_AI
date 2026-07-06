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
