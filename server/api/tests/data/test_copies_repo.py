from app.data.repositories.copies_repo import CopiesRepo
from tests.fakes import FakeSupabase


async def test_create_get_and_update():
    sb = FakeSupabase()
    repo = CopiesRepo(sb)
    copy = await repo.create({
        "jd_id": "j1", "user_id": "u1", "master_resume_id": "m1",
        "tex_content": "\\documentclass{article}", "status": "compiling",
    })
    assert (await repo.get(copy.id)).status == "compiling"
    await repo.update(copy.id, {"status": "compiled", "diff_patch": "DIFF: changed summary"})
    updated = await repo.get(copy.id)
    assert updated.status == "compiled"
    assert updated.diff_patch == "DIFF: changed summary"


async def test_list_for_user_and_count():
    sb = FakeSupabase()
    repo = CopiesRepo(sb)
    await repo.create({"jd_id": "j1", "user_id": "u1", "status": "compiled"})
    assert len(await repo.list_for_user("u1")) == 1
    assert await repo.count_for_user("u1") == 1
