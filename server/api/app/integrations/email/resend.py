from __future__ import annotations

import base64
from typing import Any, Callable


class ResendSender:
    """Wraps the Resend SDK behind the EmailSender protocol. `send_fn` is
    injectable so tests never touch the real `resend` package or network."""

    def __init__(self, api_key: str, from_addr: str, send_fn: Callable[[dict], dict] | None = None):
        self._api_key = api_key
        self._from = from_addr
        if send_fn is not None:
            self._send_fn = send_fn
        else:
            def _default_send_fn(params: dict) -> dict:
                import resend
                resend.api_key = api_key
                return resend.Emails.send(params)
            self._send_fn = _default_send_fn

    def send(
        self, to: str, subject: str, html: str, text: str,
        reply_to: str | None = None,
        attachment_bytes: bytes | None = None,
        attachment_filename: str = "attachment.pdf",
    ) -> str:
        if not self._api_key:
            raise RuntimeError("RESEND_API_KEY not configured")
        params: dict[str, Any] = {"from": self._from, "to": [to], "subject": subject, "html": html, "text": text}
        if reply_to:
            params["reply_to"] = reply_to
        if attachment_bytes:
            params["attachments"] = [{
                "filename": attachment_filename,
                "content": base64.b64encode(attachment_bytes).decode(),
            }]
        result = self._send_fn(params)
        return result.get("id", "")

    def notify(self, to: str, subject: str, html: str) -> None:
        """Best-effort user notification. Never raises — a misconfigured or
        unverified Resend domain must not abort the caller (e.g. the pipeline)."""
        if not self._api_key:
            print(f"[email skip - no RESEND_API_KEY] To: {to} | Subject: {subject}")
            return
        try:
            self._send_fn({"from": self._from, "to": [to], "subject": subject, "html": html})
        except Exception as e:
            print(f"[email FAILED - non-fatal] To: {to} | Subject: {subject} | {e}")
