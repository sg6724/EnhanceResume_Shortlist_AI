from app.services.hunter import (
    HUNTER_MONTHLY_LIMIT,
    LEADER_TITLE_RE,
    _month_key,
    hunter_quota_remaining,
    increment_hunter_quota,
    pick_leader,
)


def _p(position, confidence=90, first="Ada", last="Ng", email="ada@x.io", verification="valid"):
    return {"first_name": first, "last_name": last, "position": position,
            "value": email, "confidence": confidence,
            "verification": {"status": verification}}


def test_title_regex_matches_leader_titles():
    for t in ["CTO", "Chief Technology Officer", "Co-Founder", "founder & CEO",
              "Head of Engineering", "VP of Engineering", "co founder"]:
        assert LEADER_TITLE_RE.search(t), t


def test_title_regex_rejects_non_leaders():
    for t in ["Sales Manager", "Recruiter", "Marketing Lead", "Account Executive"]:
        assert not LEADER_TITLE_RE.search(t), t


def test_pick_leader_prefers_highest_confidence():
    people = [_p("CTO", 70, email="low@x.io"), _p("Co-Founder", 95, email="hi@x.io")]
    assert pick_leader(people)["value"] == "hi@x.io"


def test_pick_leader_ignores_non_leaders():
    assert pick_leader([_p("Sales Manager")]) is None


def test_pick_leader_empty():
    assert pick_leader([]) is None


# --- Fake Supabase client -------------------------------------------------
#
# Minimal in-memory stand-in for the subset of the async supabase-py client
# used by hunter.py: `table(...).select(...).eq(...).eq(...).maybe_single()
# .execute()` and `rpc("increment_api_quota", {...}).execute()`. It stores
# real rows and applies real filtering/upsert semantics rather than just
# recording calls, so the round-trip behavior of increment -> remaining is
# actually exercised.

class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows
        self._filters: dict = {}
        self._single = False

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def maybe_single(self):
        self._single = True
        return self

    async def execute(self):
        matches = [r for r in self._rows if all(r.get(k) == v for k, v in self._filters.items())]
        if self._single:
            return _FakeResult(matches[0] if matches else None)
        return _FakeResult(matches)


class _FakeRPC:
    def __init__(self, rows, fn_name, params):
        self._rows = rows
        self._fn_name = fn_name
        self._params = params

    async def execute(self):
        if self._fn_name != "increment_api_quota":
            raise NotImplementedError(self._fn_name)
        provider = self._params["p_provider"]
        month = self._params["p_month"]
        for row in self._rows:
            if row["provider"] == provider and row["month"] == month:
                row["count"] += 1
                return _FakeResult(row["count"])
        self._rows.append({"provider": provider, "month": month, "count": 1})
        return _FakeResult(1)


class FakeSupabase:
    def __init__(self):
        self.rows: list[dict] = []

    def table(self, _name):
        return _FakeQuery(self.rows)

    def rpc(self, fn_name, params):
        return _FakeRPC(self.rows, fn_name, params)


class _BoomQuery:
    """Fake query builder whose execute() always raises, to test error handling."""

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def maybe_single(self):
        return self

    async def execute(self):
        raise RuntimeError("boom")


class BoomSupabase:
    def table(self, _name):
        return _BoomQuery()

    def rpc(self, _fn_name, _params):
        return _BoomQuery()


# --- hunter_quota_remaining ------------------------------------------------

async def test_quota_remaining_no_row_yet():
    sb = FakeSupabase()
    assert await hunter_quota_remaining(sb) == HUNTER_MONTHLY_LIMIT


async def test_quota_remaining_reflects_existing_count():
    sb = FakeSupabase()
    sb.rows.append({"provider": "hunter", "month": _month_key(), "count": 10})
    assert await hunter_quota_remaining(sb) == HUNTER_MONTHLY_LIMIT - 10


async def test_quota_remaining_floors_at_zero():
    sb = FakeSupabase()
    sb.rows.append({"provider": "hunter", "month": _month_key(), "count": HUNTER_MONTHLY_LIMIT + 50})
    assert await hunter_quota_remaining(sb) == 0


async def test_quota_remaining_returns_zero_on_error():
    assert await hunter_quota_remaining(BoomSupabase()) == 0


# --- increment_hunter_quota --------------------------------------------------

async def test_increment_then_remaining_reflects_increment():
    sb = FakeSupabase()
    await increment_hunter_quota(sb)
    await increment_hunter_quota(sb)
    assert await hunter_quota_remaining(sb) == HUNTER_MONTHLY_LIMIT - 2


async def test_increment_swallows_errors():
    # Should not raise even though the underlying rpc call fails.
    await increment_hunter_quota(BoomSupabase())
