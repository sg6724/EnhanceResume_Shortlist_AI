from __future__ import annotations

from typing import Protocol

from ...domain.models import Contact


class ContactProvider(Protocol):
    async def find(self, company_name: str, company_domain: str | None, titles: list[str]) -> Contact | None: ...
