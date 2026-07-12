from __future__ import annotations

from app.agents import filter_agent


async def test_relevant_jd_parses_llm_json(monkeypatch):
    monkeypatch.setattr(filter_agent.settings, "gemini_api_key", "k")

    async def fake_generate(prompt, *, gemini_model, groq_model):
        return '{"relevant": true, "reason": "matches AI Engineer"}'

    monkeypatch.setattr(filter_agent, "generate", fake_generate)
    relevant, reason = await filter_agent.is_jd_relevant("some JD text", ["AI Engineer"])
    assert relevant is True
    assert reason == "matches AI Engineer"


async def test_defaults_to_pass_when_generate_raises(monkeypatch):
    monkeypatch.setattr(filter_agent.settings, "gemini_api_key", "k")

    async def fake_generate(prompt, *, gemini_model, groq_model):
        raise RuntimeError("no LLM provider available")

    monkeypatch.setattr(filter_agent, "generate", fake_generate)
    relevant, reason = await filter_agent.is_jd_relevant("some JD text", ["AI Engineer"])
    assert relevant is True
    assert "filter error" in reason


async def test_no_keys_configured_short_circuits(monkeypatch):
    monkeypatch.setattr(filter_agent.settings, "gemini_api_key", "")
    monkeypatch.setattr(filter_agent.settings, "groq_api_key", "")
    relevant, reason = await filter_agent.is_jd_relevant("x", ["AI Engineer"])
    assert relevant is True
    assert "GEMINI_API_KEY" in reason
