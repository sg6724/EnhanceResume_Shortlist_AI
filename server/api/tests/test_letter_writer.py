import pytest

from app.agents import letter_writer
from app.agents.letter_writer import validate_letter

GOOD = ("Backend engineer for Acme",
        "Hi Ada, I build FastAPI services. I shipped X and Y. "
        "I'd like to be considered for the Backend Engineer role at Acme. "
        "My resume is attached — happy to talk.")


def test_valid_letter_passes():
    assert validate_letter(*GOOD) is None


def test_empty_subject_fails():
    assert validate_letter("", GOOD[1]) is not None


def test_banned_phrase_fails():
    assert validate_letter(GOOD[0], "I hope this email finds you well. " + GOOD[1]) is not None


def test_over_220_words_fails():
    assert validate_letter(GOOD[0], "word " * 221) is not None


async def test_write_letter_returns_subject_and_body(monkeypatch):
    monkeypatch.setattr(letter_writer.settings, "gemini_api_key", "k")

    async def fake_generate(prompt, *, gemini_model, groq_model):
        return '{"subject": "Backend Engineer - Ada", "body": "' + GOOD[1] + '"}'

    monkeypatch.setattr(letter_writer, "generate", fake_generate)

    subject, body = await letter_writer.write_letter(
        resume_text="resume text",
        jd_text="jd text",
        role_title="Backend Engineer",
        founder_name="Ada",
        founder_title="CTO",
        company_name="Acme",
    )
    assert subject == "Backend Engineer - Ada"
    assert "FastAPI" in body


async def test_write_letter_raises_when_no_keys_configured(monkeypatch):
    monkeypatch.setattr(letter_writer.settings, "gemini_api_key", "")
    monkeypatch.setattr(letter_writer.settings, "groq_api_key", "")

    with pytest.raises(ValueError):
        await letter_writer.write_letter(
            resume_text="resume text", jd_text="jd text", role_title="Backend Engineer",
            founder_name="Ada", founder_title="CTO", company_name="Acme",
        )
