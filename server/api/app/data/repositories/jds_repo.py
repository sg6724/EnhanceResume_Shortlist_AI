from __future__ import annotations

from typing import Any

from ...domain.models import ScrapedJd
from .base import SupabaseRepository


class JdsRepo(SupabaseRepository):
    def __init__(self, sb: Any):
        super().__init__(sb, "scraped_jds")

    async def upsert_by_dedup_hash(self, row: dict) -> ScrapedJd:
        res = await self._query().upsert(row, on_conflict="dedup_hash").execute()
        return ScrapedJd(**res.data[0])

    async def list_for_user(self, user_id: str, limit: int = 50, offset: int = 0) -> list[ScrapedJd]:
        res = await (
            self._query().select("*").eq("user_id", user_id)
            .order("scraped_at", desc=True).range(offset, offset + limit - 1).execute()
        )
        return [ScrapedJd(**row) for row in res.data]

    async def count_for_user(self, user_id: str) -> int:
        res = await self._query().select("*").eq("user_id", user_id).execute()
        return len(res.data)
