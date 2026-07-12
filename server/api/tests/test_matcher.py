from __future__ import annotations

from app.agents import matcher


async def test_llm_score_parses_json(monkeypatch):
    monkeypatch.setattr(matcher.settings, "gemini_api_key", "k")
    monkeypatch.setattr(matcher, "compute_bm25_score", lambda jd, resume: 0.8)
    monkeypatch.setattr(matcher, "compute_semantic_score", lambda jd, resume: 0.6)

    async def fake_generate(prompt, *, gemini_model, groq_model):
        return '{"score": 0.9, "gap_analysis": "missing Docker", "reasoning": "close match"}'

    monkeypatch.setattr(matcher, "generate", fake_generate)

    result = await matcher.compute_match("jd text", "resume text", "AI Engineer")
    assert result["llm_score"] == 0.9
    assert result["gap_analysis"] == "missing Docker"
    assert result["keyword_score"] == 0.8
    assert result["semantic_score"] == 0.6
    assert result["composite_score"] == round(0.3 * 0.8 + 0.3 * 0.6 + 0.4 * 0.9, 4)


async def test_llm_error_falls_back_to_neutral(monkeypatch):
    monkeypatch.setattr(matcher.settings, "gemini_api_key", "k")
    monkeypatch.setattr(matcher, "compute_bm25_score", lambda jd, resume: 0.5)
    monkeypatch.setattr(matcher, "compute_semantic_score", lambda jd, resume: 0.5)

    async def fake_generate(prompt, *, gemini_model, groq_model):
        raise RuntimeError("no LLM provider available")

    monkeypatch.setattr(matcher, "generate", fake_generate)

    result = await matcher.compute_match("jd text", "resume text", "AI Engineer")
    assert result["llm_score"] == 0.5
    assert "LLM analysis failed" in result["gap_analysis"]
