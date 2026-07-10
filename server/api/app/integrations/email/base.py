from __future__ import annotations

from typing import Protocol


class EmailSender(Protocol):
    def send(
        self, to: str, subject: str, html: str, text: str,
        reply_to: str | None = None,
        attachment_bytes: bytes | None = None,
        attachment_filename: str = "attachment.pdf",
    ) -> str: ...

    def notify(self, to: str, subject: str, html: str) -> None: ...
