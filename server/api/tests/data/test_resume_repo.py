from app.data.repositories.resume_repo import ResumeRepo
from tests.fakes import FakeSupabase


async def test_latest_for_user_none_when_empty():
    sb = FakeSupabase()
    repo = ResumeRepo(sb)
    assert await repo.latest_for_user("u1") is None


async def test_create_new_version_increments():
    sb = FakeSupabase()
    repo = ResumeRepo(sb)
    v1 = await repo.create_new_version("u1", "\\documentclass{article} v1", "plain v1")
    assert v1.version == 1
    v2 = await repo.create_new_version("u1", "\\documentclass{article} v2", "plain v2")
    assert v2.version == 2

    latest = await repo.latest_for_user("u1")
    assert latest.version == 2
    assert latest.plain_text_cache == "plain v2"
