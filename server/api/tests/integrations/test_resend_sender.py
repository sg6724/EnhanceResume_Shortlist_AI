import base64

import pytest

from app.integrations.email.resend import ResendSender


def test_send_raises_when_no_api_key():
    sender = ResendSender(api_key="", from_addr="noreply@x.com", send_fn=lambda params: {"id": "should-not-be-called"})
    with pytest.raises(RuntimeError, match="RESEND_API_KEY"):
        sender.send(to="a@b.com", subject="Hi", html="<p>hi</p>", text="hi")


def test_send_returns_message_id_on_success():
    captured = {}

    def fake_send(params):
        captured.update(params)
        return {"id": "msg-123"}

    sender = ResendSender(api_key="key", from_addr="noreply@x.com", send_fn=fake_send)
    msg_id = sender.send(to="a@b.com", subject="Hi", html="<p>hi</p>", text="hi", reply_to="me@x.com")
    assert msg_id == "msg-123"
    assert captured["to"] == ["a@b.com"]
    assert captured["reply_to"] == "me@x.com"


def test_send_attaches_pdf_bytes_as_base64():
    captured = {}

    def fake_send(params):
        captured.update(params)
        return {"id": "msg-1"}

    sender = ResendSender(api_key="key", from_addr="noreply@x.com", send_fn=fake_send)
    sender.send(to="a@b.com", subject="Hi", html="<p>hi</p>", text="hi",
                attachment_bytes=b"%PDF-1.4", attachment_filename="resume.pdf")
    attachment = captured["attachments"][0]
    assert attachment["filename"] == "resume.pdf"
    assert base64.b64decode(attachment["content"]) == b"%PDF-1.4"


def test_notify_is_a_noop_when_no_api_key():
    sender = ResendSender(api_key="", from_addr="noreply@x.com")
    sender.notify("a@b.com", "Subject", "<p>html</p>")  # must not raise


def test_notify_swallows_send_errors():
    def failing_send(params):
        raise RuntimeError("domain not verified")

    sender = ResendSender(api_key="key", from_addr="noreply@x.com", send_fn=failing_send)
    sender.notify("a@b.com", "Subject", "<p>html</p>")  # must not raise
