from __future__ import annotations

from typing import Any

from ...domain.models import MasterResume
from .base import SupabaseRepository


class ResumeRepo(SupabaseRepository):
    def __init__(self, sb: Any):
        super().__init__(sb, "master_resume")

    async def latest_for_user(self, user_id: str) -> MasterResume | None:
        res = await (
            self._query().select("*").eq("user_id", user_id)
            .order("version", desc=True).limit(1).execute()
        )
        return MasterResume(**res.data[0]) if res.data else None

    async def create_new_version(self, user_id: str, tex_content: str, plain_text_cache: str) -> MasterResume:
        current = await self.latest_for_user(user_id)
        next_version = (current.version + 1) if current else 1
        res = await self._query().insert({
            "user_id": user_id,
            "tex_content": tex_content,
            "plain_text_cache": plain_text_cache,
            "version": next_version,
        }).execute()
        return MasterResume(**res.data[0])
