from __future__ import annotations

from typing import Any

from ...domain.models import AgentTrace
from .base import SupabaseRepository


class TracesRepo(SupabaseRepository):
    def __init__(self, sb: Any):
        super().__init__(sb, "agent_traces")

    async def log(self, jd_id: str | None, agent_name: str, log: str, reasoning: str = "") -> None:
        await self._query().insert({
            "jd_id": jd_id,
            "agent_name": agent_name,
            "log": log[:2000],
            "reasoning": reasoning[:5000],
        }).execute()

    async def list_recent(self, limit: int = 50) -> list[AgentTrace]:
        res = await self._query().select("*").order("created_at", desc=True).limit(limit).execute()
        return [AgentTrace(**row) for row in res.data]
