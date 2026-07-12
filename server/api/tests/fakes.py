from __future__ import annotations

import uuid


class FakeResult:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    """In-memory stand-in for the chained supabase-py postgrest query builder
    subset this codebase uses: select/insert/update/delete/upsert combined with
    eq/gte/lt/in_/order/limit/range/maybe_single, then execute()."""

    def __init__(self, table: list[dict]):
        self._table = table
        self._filters: list[tuple[str, str, object]] = []
        self._single = False
        self._order_col: str | None = None
        self._order_desc = False
        self._limit_n: int | None = None
        self._range: tuple[int, int] | None = None
        self._pending_insert: dict | list[dict] | None = None
        self._pending_update: dict | None = None
        self._pending_delete = False
        self._pending_upsert: dict | None = None
        self._on_conflict: str | None = None

    # --- write ops ---
    def insert(self, row):
        self._pending_insert = row
        return self

    def update(self, values):
        self._pending_update = values
        return self

    def delete(self):
        self._pending_delete = True
        return self

    def upsert(self, row, on_conflict: str | None = None):
        self._pending_upsert = row
        self._on_conflict = on_conflict
        return self

    # --- read/filter ops ---
    def select(self, *_args, **_kwargs):
        return self

    def eq(self, col, val):
        self._filters.append(("eq", col, val))
        return self

    def gte(self, col, val):
        self._filters.append(("gte", col, val))
        return self

    def lt(self, col, val):
        self._filters.append(("lt", col, val))
        return self

    def in_(self, col, vals):
        self._filters.append(("in", col, vals))
        return self

    def order(self, col, desc: bool = False):
        self._order_col = col
        self._order_desc = desc
        return self

    def limit(self, n: int):
        self._limit_n = n
        return self

    def range(self, start: int, end: int):
        self._range = (start, end)
        return self

    def maybe_single(self):
        self._single = True
        return self

    def _matches(self, row: dict) -> bool:
        for op, col, val in self._filters:
            if op == "eq" and row.get(col) != val:
                return False
            if op == "gte" and not (row.get(col) is not None and row.get(col) >= val):
                return False
            if op == "lt" and not (row.get(col) is not None and row.get(col) < val):
                return False
            if op == "in" and row.get(col) not in val:
                return False
        return True

    async def execute(self):
        if self._pending_insert is not None:
            rows = self._pending_insert if isinstance(self._pending_insert, list) else [self._pending_insert]
            inserted = []
            for row in rows:
                new_row = {"id": str(uuid.uuid4()), "created_at": "2026-01-01T00:00:00+00:00", **row}
                self._table.append(new_row)
                inserted.append(new_row)
            return FakeResult(inserted)

        if self._pending_upsert is not None:
            row = self._pending_upsert
            existing = None
            if self._on_conflict:
                existing = next((r for r in self._table if r.get(self._on_conflict) == row.get(self._on_conflict)), None)
            if existing:
                existing.update(row)
                return FakeResult([existing])
            new_row = {"id": str(uuid.uuid4()), "created_at": "2026-01-01T00:00:00+00:00", **row}
            self._table.append(new_row)
            return FakeResult([new_row])

        matches = [r for r in self._table if self._matches(r)]

        if self._pending_update is not None:
            for row in matches:
                row.update(self._pending_update)
            return FakeResult(matches)

        if self._pending_delete:
            for row in matches:
                self._table.remove(row)
            return FakeResult(matches)

        if self._order_col:
            # Sort key (None-safe): pairs a boolean "is this None" flag with the
            # value so CPython's tuple comparison resolves via `==` on equal-None
            # pairs instead of ever calling `<` on None (which raises TypeError).
            # Net effect: for ascending order, None-valued rows sort LAST; for
            # descending order (reverse=True), None-valued rows sort FIRST — this
            # matches Postgres's own default NULLS ordering (NULLS LAST for ASC,
            # NULLS FIRST for DESC).
            matches = sorted(
                matches,
                key=lambda r: (r.get(self._order_col) is None, r.get(self._order_col)),
                reverse=self._order_desc
            )
        if self._range:
            start, end = self._range
            matches = matches[start : end + 1]
        if self._limit_n is not None:
            matches = matches[: self._limit_n]

        if self._single:
            return FakeResult(matches[0] if matches else None)
        return FakeResult(matches)


class FakeSupabase:
    """In-memory stand-in for supabase.AsyncClient's `.table(name)` surface,
    keyed by table name so different tables don't collide with each other."""

    def __init__(self):
        self.tables: dict[str, list[dict]] = {}

    def table(self, name: str) -> FakeQuery:
        self.tables.setdefault(name, [])
        return FakeQuery(self.tables[name])
