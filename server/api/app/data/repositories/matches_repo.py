from __future__ import annotations

from typing import Any

from ...domain.models import JdMatch
from .base import SupabaseRepository


class MatchesRepo(SupabaseRepository):
    def __init__(self, sb: Any):
        super().__init__(sb, "jd_matches")

    async def create(self, row: dict) -> JdMatch:
        res = await self._query().insert(row).execute()
        return JdMatch(**res.data[0])

    async def get(self, match_id: str) -> JdMatch | None:
        res = await self._query().select("*").eq("id", match_id).maybe_single().execute()
        return JdMatch(**res.data) if res and res.data else None

    async def list_for_user(self, user_id: str, limit: int = 50, offset: int = 0) -> list[JdMatch]:
        res = await (
            self._query().select("*").eq("user_id", user_id)
            .order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        )
        return [JdMatch(**row) for row in res.data]

    async def count_for_user(self, user_id: str) -> int:
        res = await self._query().select("*").eq("user_id", user_id).execute()
        return len(res.data)

    async def list_above_threshold(self, user_id: str, threshold: float) -> list[JdMatch]:
        res = await self._query().select("*").eq("user_id", user_id).gte("composite_score", threshold).execute()
        return [JdMatch(**row) for row in res.data]
