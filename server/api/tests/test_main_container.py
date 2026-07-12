from app import main as main_module


async def test_lifespan_builds_container_without_database_url(monkeypatch):
    fake_sb = object()

    async def fake_acreate_client(url, key):
        return fake_sb

    monkeypatch.setattr(main_module, "acreate_client", fake_acreate_client)
    monkeypatch.setattr(main_module.settings, "database_url", "")

    async with main_module.lifespan(main_module.app):
        container = main_module.app.state.container
        assert container is not None
        assert container.sb is fake_sb
        assert len(container.job_sources) == 2
        assert len(container.contact_providers) == 1
