from app.agents.contact_finder import guess_emails, candidate_domains


def test_guess_emails_patterns():
    assert guess_emails("Ada", "Ng", "x.io") == ["ada@x.io", "ada.ng@x.io", "ang@x.io"]


def test_guess_emails_handles_missing_last():
    assert guess_emails("Ada", "", "x.io") == ["ada@x.io"]


def test_candidate_domains_normalizes():
    assert candidate_domains("Acme Labs, Inc.") == ["acmelabs.com", "acmelabs.io", "acmelabs.ai"]


def test_candidate_domains_strips_suffixes():
    for name in ["Acme Inc", "Acme LLC", "Acme Ltd.", "Acme Technologies Pvt Ltd"]:
        assert candidate_domains(name)[0].startswith("acme"), name
