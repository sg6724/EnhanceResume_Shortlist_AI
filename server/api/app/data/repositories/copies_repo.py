from __future__ import annotations

from typing import Any

from ...domain.models import ResumeCopy
from .base import SupabaseRepository


class CopiesRepo(SupabaseRepository):
    def __init__(self, sb: Any):
        super().__init__(sb, "resume_copies")

    async def create(self, row: dict) -> ResumeCopy:
        res = await self._query().insert(row).execute()
        return ResumeCopy(**res.data[0])

    async def get(self, copy_id: str) -> ResumeCopy | None:
        res = await self._query().select("*").eq("id", copy_id).maybe_single().execute()
        return ResumeCopy(**res.data) if res and res.data else None

    async def list_for_user(self, user_id: str) -> list[ResumeCopy]:
        res = await self._query().select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return [ResumeCopy(**row) for row in res.data]

    async def update(self, copy_id: str, values: dict) -> None:
        await self._query().update(values).eq("id", copy_id).execute()

    async def count_for_user(self, user_id: str) -> int:
        res = await self._query().select("*").eq("user_id", user_id).execute()
        return len(res.data)
