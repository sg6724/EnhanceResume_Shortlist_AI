from __future__ import annotations

from fastapi import APIRouter, Request
from typing import Optional

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("")
async def list_traces(request: Request, jd_id: Optional[str] = None, limit: int = 100):
    sb = request.app.state.supabase
    q = sb.table("agent_traces").select("*").order("created_at", desc=True).limit(limit)
    if jd_id:
        q = q.eq("jd_id", jd_id)
    res = await q.execute()
    return res.data
