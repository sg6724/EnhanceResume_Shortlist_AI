from __future__ import annotations

from typing import Any

from ...domain.models import Position
from .base import SupabaseRepository


class PositionsRepo(SupabaseRepository):
    def __init__(self, sb: Any):
        super().__init__(sb, "target_positions")

    async def list_active_for_user(self, user_id: str) -> list[Position]:
        res = await self._query().select("*").eq("user_id", user_id).eq("is_active", True).execute()
        return [Position(**row) for row in res.data]

    async def list_all_for_user(self, user_id: str) -> list[Position]:
        res = await self._query().select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return [Position(**row) for row in res.data]

    async def create(self, user_id: str, title: str, fuzzy_keywords: list[str]) -> Position:
        res = await self._query().insert(
            {"user_id": user_id, "title": title, "fuzzy_keywords": fuzzy_keywords, "is_active": True}
        ).execute()
        return Position(**res.data[0])

    async def toggle_active(self, position_id: str) -> Position | None:
        cur = await self._query().select("is_active").eq("id", position_id).maybe_single().execute()
        if not cur.data:
            return None
        res = await self._query().update({"is_active": not cur.data["is_active"]}).eq("id", position_id).execute()
        return Position(**res.data[0])

    async def delete(self, position_id: str) -> None:
        await self._query().delete().eq("id", position_id).execute()
