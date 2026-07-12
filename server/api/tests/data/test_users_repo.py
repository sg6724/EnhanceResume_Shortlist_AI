from app.data.repositories.users_repo import UsersRepo
from tests.fakes import FakeSupabase


async def test_get_by_email_found():
    sb = FakeSupabase()
    sb.tables["users"] = [{
        "id": "u1", "email": "a@b.com", "match_threshold": 0.6, "top_n": 5,
        "timeout_minutes": 30, "max_compiler_retries": 3, "outreach_enabled": True,
        "outreach_interval_hours": 24, "outreach_batch_size": 3,
    }]
    repo = UsersRepo(sb)
    user = await repo.get_by_email("a@b.com")
    assert user is not None
    assert user.id == "u1"
    assert user.top_n == 5


async def test_get_by_email_not_found():
    sb = FakeSupabase()
    repo = UsersRepo(sb)
    assert await repo.get_by_email("missing@b.com") is None


async def test_update_outreach_last_run():
    sb = FakeSupabase()
    sb.tables["users"] = [{
        "id": "u1", "email": "a@b.com", "match_threshold": 0.6, "top_n": 5,
        "timeout_minutes": 30, "max_compiler_retries": 3, "outreach_enabled": True,
        "outreach_interval_hours": 24, "outreach_batch_size": 3,
        "outreach_last_run_at": None,
    }]
    repo = UsersRepo(sb)
    await repo.update_outreach_last_run("u1", "2026-07-09T12:00:00+00:00")
    assert sb.tables["users"][0]["outreach_last_run_at"] == "2026-07-09T12:00:00+00:00"
