from app.data.repositories.positions_repo import PositionsRepo
from tests.fakes import FakeSupabase


async def test_create_and_list_active():
    sb = FakeSupabase()
    repo = PositionsRepo(sb)
    created = await repo.create("u1", "AI Engineer", ["ML Engineer", "LLM Engineer"])
    assert created.title == "AI Engineer"
    assert created.is_active is True

    active = await repo.list_active_for_user("u1")
    assert len(active) == 1
    assert active[0].fuzzy_keywords == ["ML Engineer", "LLM Engineer"]


async def test_list_all_for_user_excludes_other_users():
    sb = FakeSupabase()
    repo = PositionsRepo(sb)
    await repo.create("u1", "AI Engineer", [])
    await repo.create("u2", "Data Scientist", [])

    mine = await repo.list_all_for_user("u1")
    assert len(mine) == 1
    assert mine[0].title == "AI Engineer"


async def test_toggle_active_flips_flag():
    sb = FakeSupabase()
    repo = PositionsRepo(sb)
    created = await repo.create("u1", "AI Engineer", [])
    toggled = await repo.toggle_active(created.id)
    assert toggled.is_active is False
    toggled_again = await repo.toggle_active(created.id)
    assert toggled_again.is_active is True


async def test_toggle_active_missing_returns_none():
    sb = FakeSupabase()
    repo = PositionsRepo(sb)
    assert await repo.toggle_active("does-not-exist") is None


async def test_delete_removes_row():
    sb = FakeSupabase()
    repo = PositionsRepo(sb)
    created = await repo.create("u1", "AI Engineer", [])
    await repo.delete(created.id)
    assert await repo.list_all_for_user("u1") == []
