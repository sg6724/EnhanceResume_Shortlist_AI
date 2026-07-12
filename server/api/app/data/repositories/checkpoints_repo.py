from __future__ import annotations

from typing import Any

from ...domain.models import Checkpoint
from .base import SupabaseRepository


class CheckpointsRepo(SupabaseRepository):
    def __init__(self, sb: Any):
        super().__init__(sb, "checkpoint_state")

    async def create(self, row: dict) -> Checkpoint:
        res = await self._query().insert(row).execute()
        return Checkpoint(**res.data[0])

    async def get(self, checkpoint_id: str) -> Checkpoint | None:
        res = await self._query().select("*").eq("id", checkpoint_id).maybe_single().execute()
        return Checkpoint(**res.data) if res and res.data else None

    async def list_for_user(self, user_id: str) -> list[Checkpoint]:
        res = await self._query().select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return [Checkpoint(**row) for row in res.data]

    async def update_status(self, checkpoint_id: str, status: str) -> None:
        await self._query().update({"status": status}).eq("id", checkpoint_id).execute()

    async def count_pending_for_user(self, user_id: str) -> int:
        res = await self._query().select("*").eq("user_id", user_id).eq("status", "pending").execute()
        return len(res.data)
