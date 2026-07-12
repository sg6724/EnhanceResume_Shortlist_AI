from __future__ import annotations

from typing import Protocol

from ...domain.models import CompileResult


class CompileClient(Protocol):
    async def compile(self, tex: str, engine: str = "pdflatex", jobname: str = "resume") -> CompileResult: ...
