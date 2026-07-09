from app.data.repositories.traces_repo import TracesRepo
from tests.fakes import FakeSupabase


async def test_log_and_list_recent():
    sb = FakeSupabase()
    repo = TracesRepo(sb)
    await repo.log("j1", "matcher", "Score: 0.61", "gap analysis text")
    recent = await repo.list_recent(limit=10)
    assert len(recent) == 1
    assert recent[0].agent_name == "matcher"
    assert recent[0].reasoning == "gap analysis text"


async def test_log_truncates_long_fields():
    sb = FakeSupabase()
    repo = TracesRepo(sb)
    await repo.log("j1", "rewriter", "x" * 3000, "y" * 6000)
    recent = await repo.list_recent(limit=10)
    assert len(recent[0].log) == 2000
    assert len(recent[0].reasoning) == 5000
