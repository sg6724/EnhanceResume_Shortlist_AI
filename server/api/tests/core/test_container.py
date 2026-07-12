import httpx

from app.core.config import Settings
from app.core.container import build_container
from app.data.repositories.checkpoints_repo import CheckpointsRepo
from app.data.repositories.positions_repo import PositionsRepo
from tests.fakes import FakeSupabase


def _settings() -> Settings:
    return Settings(
        supabase_url="https://x.supabase.co",
        supabase_service_key="svc-key",
        gemini_api_key="gem-key",
        resend_api_key="",
        hunter_api_key="",
        apollo_api_key="apollo-key",
        adzuna_app_id="",
        adzuna_api_key="",
    )


async def test_build_container_wires_repositories():
    sb = FakeSupabase()
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    container = build_container(_settings(), sb, http)
    await http.aclose()

    assert isinstance(container.positions, PositionsRepo)
    assert isinstance(container.checkpoints, CheckpointsRepo)
    assert container.sb is sb


async def test_build_container_wires_job_sources_and_contact_providers():
    sb = FakeSupabase()
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    container = build_container(_settings(), sb, http)
    await http.aclose()

    assert len(container.job_sources) == 2  # RemoteOK + Adzuna
    assert len(container.contact_providers) == 1  # SiteScrapeProvider only, until Phase 3 adds Apollo


async def test_build_container_does_not_touch_network():
    sb = FakeSupabase()

    def blow_up(request: httpx.Request) -> httpx.Response:
        raise AssertionError("build_container must not make network calls")

    http = httpx.AsyncClient(transport=httpx.MockTransport(blow_up))
    container = build_container(_settings(), sb, http)
    await http.aclose()
    assert container is not None
