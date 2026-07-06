from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    db_ok = True
    try:
        await request.app.state.supabase.table("users").select("id").limit(1).execute()
    except Exception:
        db_ok = False
    return {"status": "ok", "db": db_ok}
