from app.data.repositories.jds_repo import JdsRepo
from tests.fakes import FakeSupabase


async def test_upsert_by_dedup_hash_inserts_new():
    sb = FakeSupabase()
    repo = JdsRepo(sb)
    jd = await repo.upsert_by_dedup_hash({
        "user_id": "u1", "source": "remoteok", "company": "Acme", "title": "AI Engineer",
        "location": "Remote", "url": "https://x", "raw_text": "x" * 150,
        "relevance_confirmed": True, "dedup_hash": "hash1",
    })
    assert jd.company == "Acme"
    assert len(sb.tables["scraped_jds"]) == 1


async def test_upsert_by_dedup_hash_updates_existing():
    sb = FakeSupabase()
    repo = JdsRepo(sb)
    await repo.upsert_by_dedup_hash({
        "user_id": "u1", "source": "remoteok", "company": "Acme", "title": "AI Engineer",
        "location": "Remote", "url": "https://x", "raw_text": "x" * 150,
        "relevance_confirmed": True, "dedup_hash": "hash1",
    })
    updated = await repo.upsert_by_dedup_hash({
        "user_id": "u1", "source": "remoteok", "company": "Acme", "title": "Senior AI Engineer",
        "location": "Remote", "url": "https://x", "raw_text": "y" * 150,
        "relevance_confirmed": True, "dedup_hash": "hash1",
    })
    assert updated.title == "Senior AI Engineer"
    assert len(sb.tables["scraped_jds"]) == 1


async def test_list_for_user_and_count():
    sb = FakeSupabase()
    repo = JdsRepo(sb)
    for i in range(3):
        await repo.upsert_by_dedup_hash({
            "user_id": "u1", "source": "remoteok", "company": f"Co{i}", "title": "AI Engineer",
            "location": "Remote", "url": "https://x", "raw_text": "x" * 150,
            "relevance_confirmed": True, "dedup_hash": f"hash{i}",
        })
    jds = await repo.list_for_user("u1")
    assert len(jds) == 3
    assert await repo.count_for_user("u1") == 3
