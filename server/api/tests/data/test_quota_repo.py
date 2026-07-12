from app.data.repositories.quota_repo import QuotaRepo
from tests.fakes import FakeResult, FakeSupabase


class _RpcAwareFakeSupabase(FakeSupabase):
    """Extends FakeSupabase with the `increment_api_quota` RPC used by QuotaRepo."""

    def rpc(self, fn_name: str, params: dict):
        return _FakeRpcCall(self, fn_name, params)


class _FakeRpcCall:
    def __init__(self, sb: _RpcAwareFakeSupabase, fn_name: str, params: dict):
        self._sb = sb
        self._fn_name = fn_name
        self._params = params

    async def execute(self):
        assert self._fn_name == "increment_api_quota"
        provider = self._params["p_provider"]
        month = self._params["p_month"]
        rows = self._sb.tables.setdefault("api_quota_usage", [])
        for row in rows:
            if row["provider"] == provider and row["month"] == month:
                row["count"] += 1
                return FakeResult(row["count"])
        rows.append({"provider": provider, "month": month, "count": 1})
        return FakeResult(1)


async def test_remaining_with_no_usage_row():
    sb = _RpcAwareFakeSupabase()
    repo = QuotaRepo(sb)
    assert await repo.remaining("apollo", monthly_limit=100) == 100


async def test_increment_then_remaining_reflects_usage():
    sb = _RpcAwareFakeSupabase()
    repo = QuotaRepo(sb)
    await repo.increment("apollo")
    await repo.increment("apollo")
    assert await repo.remaining("apollo", monthly_limit=100) == 98


async def test_remaining_floors_at_zero():
    sb = _RpcAwareFakeSupabase()
    sb.tables["api_quota_usage"] = [{"provider": "apollo", "month": repo_month(), "count": 500}]
    repo = QuotaRepo(sb)
    assert await repo.remaining("apollo", monthly_limit=100) == 0


def repo_month() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m")
