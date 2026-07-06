from __future__ import annotations

from ..config import settings


def send_notification(to: str, subject: str, html: str) -> None:
    if not settings.resend_api_key:
        print(f"[email skip — no RESEND_API_KEY] To: {to} | Subject: {subject}")
        return
    import resend
    resend.api_key = settings.resend_api_key
    resend.Emails.send({
        "from": settings.resend_from,
        "to": [to],
        "subject": subject,
        "html": html,
    })


def notify_batch_complete(to: str, match_count: int, zero_matches: bool = False) -> None:
    if zero_matches:
        send_notification(
            to,
            "JobHunt AI: No strong matches found",
            "<p>The latest scraping batch found <strong>no JDs</strong> above your match threshold.</p>"
            "<p>Try lowering your threshold or adding more target positions.</p>",
        )
    else:
        send_notification(
            to,
            f"JobHunt AI: {match_count} new match{'es' if match_count != 1 else ''} ready",
            f"<p><strong>{match_count}</strong> tailored resume "
            f"{'copies are' if match_count != 1 else 'copy is'} ready for your review.</p>"
            f"<p>Open <a href='http://localhost:3000/checkpoints'>your dashboard</a> to approve.</p>",
        )


def notify_compile_failed(to: str, company: str, title: str) -> None:
    send_notification(
        to,
        f"JobHunt AI: Compile failed — {title} at {company}",
        f"<p>Resume compilation failed after all retries for "
        f"<strong>{title}</strong> at {company}.</p>"
        f"<p>Check the <a href='http://localhost:3000/traces'>Observability panel</a> for the error log.</p>",
    )
