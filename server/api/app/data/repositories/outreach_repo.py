from __future__ import annotations

from typing import Any

from ...domain.models import OutreachDraft, OutreachTarget
from .base import SupabaseRepository


class OutreachTargetsRepo(SupabaseRepository):
    def __init__(self, sb: Any):
        super().__init__(sb, "outreach_targets")

    async def create(self, row: dict) -> OutreachTarget:
        res = await self._query().insert(row).execute()
        return OutreachTarget(**res.data[0])

    async def get(self, target_id: str) -> OutreachTarget | None:
        res = await self._query().select("*").eq("id", target_id).maybe_single().execute()
        return OutreachTarget(**res.data) if res and res.data else None

    async def list_for_user(self, user_id: str) -> list[OutreachTarget]:
        res = await self._query().select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return [OutreachTarget(**row) for row in res.data]

    async def list_by_company_names_lower(self, user_id: str) -> set[str]:
        res = await self._query().select("company_name").eq("user_id", user_id).execute()
        return {row["company_name"].lower() for row in res.data}

    async def list_pending_batch(
        self, user_id: str, statuses: list[str], max_attempts: int, batch_size: int,
    ) -> list[OutreachTarget]:
        res = await (
            self._query().select("*").eq("user_id", user_id).in_("status", statuses)
            .lt("attempts", max_attempts).order("created_at").limit(batch_size).execute()
        )
        return [OutreachTarget(**row) for row in res.data]

    async def update(self, target_id: str, values: dict) -> None:
        await self._query().update(values).eq("id", target_id).execute()

    async def delete(self, target_id: str) -> None:
        await self._query().delete().eq("id", target_id).execute()


class OutreachDraftsRepo(SupabaseRepository):
    def __init__(self, sb: Any):
        super().__init__(sb, "outreach_drafts")

    async def create(self, row: dict) -> OutreachDraft:
        res = await self._query().insert(row).execute()
        return OutreachDraft(**res.data[0])

    async def get(self, draft_id: str) -> OutreachDraft | None:
        res = await self._query().select("*").eq("id", draft_id).maybe_single().execute()
        return OutreachDraft(**res.data) if res and res.data else None

    async def update(self, draft_id: str, values: dict) -> OutreachDraft | None:
        res = await self._query().update(values).eq("id", draft_id).execute()
        return OutreachDraft(**res.data[0]) if res.data else None

    async def list_pending_for_user(self, user_id: str, target_rows: list[dict]) -> list[OutreachDraft]:
        """Drafts whose target belongs to `user_id`, is still status='drafted',
        and hasn't been sent yet. `target_rows` is the caller's own targets
        table snapshot (the real Supabase impl instead joins server-side)."""
        drafted_target_ids = {
            t["id"] for t in target_rows if t.get("user_id") == user_id and t.get("status") == "drafted"
        }
        res = await self._query().select("*").execute()
        return [
            OutreachDraft(**row) for row in res.data
            if row["target_id"] in drafted_target_ids and not row.get("sent_at")
        ]
