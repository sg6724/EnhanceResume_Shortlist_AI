from app.data.repositories.outreach_repo import OutreachDraftsRepo, OutreachTargetsRepo
from tests.fakes import FakeSupabase


async def test_targets_create_get_update_delete():
    sb = FakeSupabase()
    repo = OutreachTargetsRepo(sb)
    t = await repo.create({"user_id": "u1", "company_name": "Acme", "status": "drafted"})
    assert (await repo.get(t.id)).company_name == "Acme"
    await repo.update(t.id, {"status": "approved"})
    updated = await repo.get(t.id)
    assert updated.status == "approved"
    await repo.delete(t.id)
    assert await repo.get(t.id) is None


async def test_list_for_user():
    sb = FakeSupabase()
    repo = OutreachTargetsRepo(sb)
    await repo.create({"user_id": "u1", "company_name": "Acme", "status": "drafted"})
    await repo.create({"user_id": "u2", "company_name": "Other", "status": "drafted"})
    rows = await repo.list_for_user("u1")
    assert [r.company_name for r in rows] == ["Acme"]


async def test_drafts_create_get_update():
    sb = FakeSupabase()
    repo = OutreachDraftsRepo(sb)
    d = await repo.create({"target_id": "t1", "subject": "Hi", "body": "Body"})
    assert (await repo.get(d.id)).subject == "Hi"
    updated = await repo.update(d.id, {"edited_subject": "New subject"})
    assert updated.edited_subject == "New subject"
