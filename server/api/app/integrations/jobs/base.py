from __future__ import annotations

from typing import Protocol

from ...domain.models import RawJd


class JobSource(Protocol):
    async def fetch(self, keywords: list[str]) -> list[RawJd]: ...
