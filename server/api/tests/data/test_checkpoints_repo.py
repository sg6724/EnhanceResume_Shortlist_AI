from app.data.repositories.checkpoints_repo import CheckpointsRepo
from tests.fakes import FakeSupabase


async def test_create_get_and_update_status():
    sb = FakeSupabase()
    repo = CheckpointsRepo(sb)
    cp = await repo.create({"jd_id": "j1", "user_id": "u1", "planned_diff": "diff", "status": "pending"})
    assert (await repo.get(cp.id)).status == "pending"
    await repo.update_status(cp.id, "approved")
    assert (await repo.get(cp.id)).status == "approved"


async def test_list_for_user_and_count_pending():
    sb = FakeSupabase()
    repo = CheckpointsRepo(sb)
    await repo.create({"jd_id": "j1", "user_id": "u1", "status": "pending"})
    await repo.create({"jd_id": "j2", "user_id": "u1", "status": "approved"})
    assert len(await repo.list_for_user("u1")) == 2
    assert await repo.count_pending_for_user("u1") == 1
