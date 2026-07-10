import httpx

from app.integrations.contacts.sitescrape import SiteScrapeProvider, candidate_domains, guess_emails


def test_candidate_domains_strips_legal_suffix():
    assert candidate_domains("Acme Inc.") == ["acme.com", "acme.io", "acme.ai"]


def test_candidate_domains_empty_for_blank_name():
    assert candidate_domains("") == []


def test_guess_emails_patterns():
    assert guess_emails("Ada", "Ng", "acme.com") == [
        "ada@acme.com", "ada.ng@acme.com", "ang@acme.com",
    ]


def test_guess_emails_no_last_name():
    assert guess_emails("Ada", "", "acme.com") == ["ada@acme.com"]


class _FakeLlm:
    def __init__(self, people_json: str):
        self._people_json = people_json
        self.prompts: list[str] = []

    async def generate(self, model: str, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._people_json

    def embed(self, model, text):
        raise NotImplementedError


def _homepage_response(request: httpx.Request) -> httpx.Response:
    if str(request.url) == "https://acme.com":
        return httpx.Response(200, text="<html><head><title>Acme - Home</title></head><body>Welcome</body></html>")
    if str(request.url).startswith("https://acme.com/about"):
        return httpx.Response(200, text="<html><body>Ada Ng is our CTO and co-founder.</body></html>")
    return httpx.Response(404)


async def test_find_returns_contact_when_leader_extracted():
    llm = _FakeLlm('{"people": [{"name": "Ada Ng", "title": "CTO"}]}')
    http = httpx.AsyncClient(transport=httpx.MockTransport(_homepage_response))
    provider = SiteScrapeProvider(http=http, llm=llm)

    contact = await provider.find("Acme", None, ["cto", "founder"])
    await http.aclose()

    assert contact is not None
    assert contact.founder_name == "Ada Ng"
    assert contact.founder_email == "ada@acme.com"
    assert contact.contact_method == "scraped"
    assert contact.email_confidence == "guessed"


async def test_find_returns_none_when_domain_unresolvable():
    llm = _FakeLlm('{"people": []}')
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    provider = SiteScrapeProvider(http=http, llm=llm)

    contact = await provider.find("Totally Unknown Startup", None, ["cto"])
    await http.aclose()
    assert contact is None


async def test_find_returns_none_when_no_leaders_found():
    llm = _FakeLlm('{"people": []}')
    http = httpx.AsyncClient(transport=httpx.MockTransport(_homepage_response))
    provider = SiteScrapeProvider(http=http, llm=llm)

    contact = await provider.find("Acme", "acme.com", ["cto"])
    await http.aclose()
    assert contact is None
