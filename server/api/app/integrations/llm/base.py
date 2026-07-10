from __future__ import annotations

from typing import Protocol


class LlmClient(Protocol):
    async def generate(self, model: str, prompt: str) -> str: ...

    def embed(self, model: str, text: str) -> list[float]: ...
