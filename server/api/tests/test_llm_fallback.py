from __future__ import annotations

import pytest

from app.services import llm


class _FakeResp:
    def __init__(self, text):
        self.text = text


class _FakeGeminiModels:
    def __init__(self, text=None, exc=None):
        self._text = text
        self._exc = exc

    async def generate_content(self, model, contents):
        if self._exc:
            raise self._exc
        return _FakeResp(self._text)


class _FakeGeminiAio:
    def __init__(self, text=None, exc=None):
        self.models = _FakeGeminiModels(text, exc)


class _FakeGeminiClient:
    def __init__(self, text=None, exc=None):
        self.aio = _FakeGeminiAio(text, exc)


class _FakeGroqMessage:
    def __init__(self, content):
        self.content = content


class _FakeGroqChoice:
    def __init__(self, content):
        self.message = _FakeGroqMessage(content)


class _FakeGroqCompletion:
    def __init__(self, content):
        self.choices = [_FakeGroqChoice(content)]


class _FakeGroqCompletions:
    def __init__(self, text=None, exc=None):
        self._text = text
        self._exc = exc

    async def create(self, model, messages):
        if self._exc:
            raise self._exc
        return _FakeGroqCompletion(self._text)


class _FakeGroqChat:
    def __init__(self, text=None, exc=None):
        self.completions = _FakeGroqCompletions(text, exc)


class _FakeGroqClient:
    def __init__(self, text=None, exc=None):
        self.chat = _FakeGroqChat(text, exc)


async def test_generate_uses_gemini_when_it_succeeds(monkeypatch):
    monkeypatch.setattr(llm.settings, "gemini_api_key", "g-key")
    monkeypatch.setattr(llm.settings, "groq_api_key", "q-key")
    monkeypatch.setattr(llm, "get_client", lambda: _FakeGeminiClient(text="from gemini"))

    calls = {"groq": 0}

    def _groq_should_not_be_called():
        calls["groq"] += 1
        return _FakeGroqClient(text="from groq")

    monkeypatch.setattr(llm, "get_groq_client", _groq_should_not_be_called)

    result = await llm.generate("prompt", gemini_model="gm", groq_model="qm")
    assert result == "from gemini"
    assert calls["groq"] == 0


async def test_generate_falls_back_to_groq_when_gemini_raises(monkeypatch):
    monkeypatch.setattr(llm.settings, "gemini_api_key", "g-key")
    monkeypatch.setattr(llm.settings, "groq_api_key", "q-key")
    monkeypatch.setattr(llm, "get_client", lambda: _FakeGeminiClient(exc=RuntimeError("429 quota exceeded")))
    monkeypatch.setattr(llm, "get_groq_client", lambda: _FakeGroqClient(text="from groq"))

    result = await llm.generate("prompt", gemini_model="gm", groq_model="qm")
    assert result == "from groq"


async def test_generate_raises_when_both_fail(monkeypatch):
    monkeypatch.setattr(llm.settings, "gemini_api_key", "g-key")
    monkeypatch.setattr(llm.settings, "groq_api_key", "q-key")
    monkeypatch.setattr(llm, "get_client", lambda: _FakeGeminiClient(exc=RuntimeError("gemini down")))
    monkeypatch.setattr(llm, "get_groq_client", lambda: _FakeGroqClient(exc=RuntimeError("groq down")))

    with pytest.raises(RuntimeError) as exc_info:
        await llm.generate("prompt", gemini_model="gm", groq_model="qm")
    assert "gemini down" in str(exc_info.value)
    assert "groq down" in str(exc_info.value)


async def test_generate_uses_groq_only_when_no_gemini_key(monkeypatch):
    monkeypatch.setattr(llm.settings, "gemini_api_key", "")
    monkeypatch.setattr(llm.settings, "groq_api_key", "q-key")

    calls = {"gemini": 0}

    def _gemini_should_not_be_called():
        calls["gemini"] += 1
        return _FakeGeminiClient(text="from gemini")

    monkeypatch.setattr(llm, "get_client", _gemini_should_not_be_called)
    monkeypatch.setattr(llm, "get_groq_client", lambda: _FakeGroqClient(text="from groq"))

    result = await llm.generate("prompt", gemini_model="gm", groq_model="qm")
    assert result == "from groq"
    assert calls["gemini"] == 0


async def test_generate_raises_immediately_when_no_keys_configured(monkeypatch):
    monkeypatch.setattr(llm.settings, "gemini_api_key", "")
    monkeypatch.setattr(llm.settings, "groq_api_key", "")

    with pytest.raises(RuntimeError) as exc_info:
        await llm.generate("prompt", gemini_model="gm", groq_model="qm")
    assert "no GEMINI_API_KEY" in str(exc_info.value)
    assert "no GROQ_API_KEY" in str(exc_info.value)
