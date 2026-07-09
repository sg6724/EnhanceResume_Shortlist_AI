from __future__ import annotations

from typing import Any


class SupabaseRepository:
    """Base class for repositories. Holds the shared async Supabase client and
    the table this repository owns; this is the ONLY place that table name
    should appear for its aggregate."""

    def __init__(self, sb: Any, table: str):
        self._sb = sb
        self._table = table

    def _query(self):
        return self._sb.table(self._table)
