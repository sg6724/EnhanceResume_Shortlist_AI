from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .base import SupabaseRepository


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


class QuotaRepo(SupabaseRepository):
    """Generalizes the existing per-provider monthly quota pattern (previously
    hardcoded to 'hunter' in services/hunter.py) to any provider, e.g. 'apollo'."""

    def __init__(self, sb: Any):
        super().__init__(sb, "api_quota_usage")

    async def remaining(self, provider: str, monthly_limit: int) -> int:
        try:
            res = await (
                self._query().select("count").eq("provider", provider)
                .eq("month", _month_key()).maybe_single().execute()
            )
        except Exception:
            return 0
        used = res.data["count"] if res and res.data else 0
        return max(0, monthly_limit - used)

    async def increment(self, provider: str) -> None:
        try:
            await self._sb.rpc(
                "increment_api_quota", {"p_provider": provider, "p_month": _month_key()}
            ).execute()
        except Exception:
            pass
