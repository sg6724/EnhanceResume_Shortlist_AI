from app.data.repositories.matches_repo import MatchesRepo
from tests.fakes import FakeSupabase


async def test_create_and_get():
    sb = FakeSupabase()
    repo = MatchesRepo(sb)
    m = await repo.create({
        "jd_id": "j1", "user_id": "u1", "position_context": "AI Engineer",
        "keyword_score": 0.2, "semantic_score": 0.6, "llm_score": 0.7,
        "composite_score": 0.56, "gap_analysis": "missing RAG experience",
    })
    fetched = await repo.get(m.id)
    assert fetched.composite_score == 0.56


async def test_list_for_user_and_count():
    sb = FakeSupabase()
    repo = MatchesRepo(sb)
    for i in range(2):
        await repo.create({"jd_id": f"j{i}", "user_id": "u1", "composite_score": 0.5})
    assert await repo.count_for_user("u1") == 2
    assert len(await repo.list_for_user("u1")) == 2


async def test_list_above_threshold():
    sb = FakeSupabase()
    repo = MatchesRepo(sb)
    await repo.create({"jd_id": "j1", "user_id": "u1", "composite_score": 0.7})
    await repo.create({"jd_id": "j2", "user_id": "u1", "composite_score": 0.3})
    above = await repo.list_above_threshold("u1", 0.6)
    assert len(above) == 1
    assert above[0].jd_id == "j1"
