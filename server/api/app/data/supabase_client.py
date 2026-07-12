from __future__ import annotations

from supabase import AsyncClient, acreate_client

from ..core.config import settings


async def create_supabase_client() -> AsyncClient:
    return await acreate_client(settings.db.supabase_url, settings.db.supabase_service_key)
