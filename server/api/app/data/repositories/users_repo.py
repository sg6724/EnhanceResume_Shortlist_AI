from __future__ import annotations

from typing import Any

from ...domain.models import User
from .base import SupabaseRepository


class UsersRepo(SupabaseRepository):
    def __init__(self, sb: Any):
        super().__init__(sb, "users")

    async def get_by_email(self, email: str) -> User | None:
        res = await self._query().select("*").eq("email", email).maybe_single().execute()
        return User(**res.data) if res and res.data else None

    async def update_outreach_last_run(self, user_id: str, when_iso: str) -> None:
        await self._query().update({"outreach_last_run_at": when_iso}).eq("id", user_id).execute()
