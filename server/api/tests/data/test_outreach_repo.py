from app.data.repositories.outreach_repo import OutreachDraftsRepo, OutreachTargetsRepo
from tests.fakes import FakeSupabase


async def test_targets_create_get_update_delete():
    sb = FakeSupabase()
    repo = OutreachTargetsRepo(sb)
    t = await repo.create({"user_id": "u1", "company_name": "Acme", "status": "pending"})
    assert (await repo.get(t.id)).company_name == "Acme"
    await repo.update(t.id, {"status": "contact_found", "founder_email": "a@acme.com"})
    updated = await repo.get(t.id)
    assert updated.status == "contact_found"
    assert updated.founder_email == "a@acme.com"
    await repo.delete(t.id)
    assert await repo.get(t.id) is None


async def test_list_by_company_names_lower():
    sb = FakeSupabase()
    repo = OutreachTargetsRepo(sb)
    await repo.create({"user_id": "u1", "company_name": "Acme Corp", "status": "pending"})
    names = await repo.list_by_company_names_lower("u1")
    assert names == {"acme corp"}


async def test_list_pending_batch_respects_status_attempts_and_batch_size():
    sb = FakeSupabase()
    repo = OutreachTargetsRepo(sb)
    await repo.create({"user_id": "u1", "company_name": "A", "status": "pending", "attempts": 0})
    await repo.create({"user_id": "u1", "company_name": "B", "status": "contact_found", "attempts": 1})
    await repo.create({"user_id": "u1", "company_name": "C", "status": "sent", "attempts": 1})
    await repo.create({"user_id": "u1", "company_name": "D", "status": "pending", "attempts": 5})

    batch = await repo.list_pending_batch("u1", ["pending", "contact_found"], max_attempts=3, batch_size=10)
    names = {t.company_name for t in batch}
    assert names == {"A", "B"}


async def test_drafts_create_get_update():
    sb = FakeSupabase()
    repo = OutreachDraftsRepo(sb)
    d = await repo.create({"target_id": "t1", "subject": "Hi", "body": "Body"})
    assert (await repo.get(d.id)).subject == "Hi"
    updated = await repo.update(d.id, {"edited_subject": "New subject"})
    assert updated.edited_subject == "New subject"


async def test_list_pending_for_user_filters_drafted_and_unsent():
    sb = FakeSupabase()
    targets_repo = OutreachTargetsRepo(sb)
    drafts_repo = OutreachDraftsRepo(sb)
    t1 = await targets_repo.create({"user_id": "u1", "company_name": "A", "status": "drafted"})
    t2 = await targets_repo.create({"user_id": "u1", "company_name": "B", "status": "sent"})
    await drafts_repo.create({"target_id": t1.id, "subject": "S1", "body": "B1"})
    d2 = await drafts_repo.create({"target_id": t2.id, "subject": "S2", "body": "B2"})
    await drafts_repo.update(d2.id, {"sent_at": "2026-07-09T00:00:00+00:00"})

    pending = await drafts_repo.list_pending_for_user("u1", sb.tables["outreach_targets"])
    assert len(pending) == 1
    assert pending[0].subject == "S1"
