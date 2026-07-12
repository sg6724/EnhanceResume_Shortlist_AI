from __future__ import annotations

import asyncio
import time

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


async def test_slow_semantic_score_does_not_block_event_loop(monkeypatch):
    """compute_semantic_score is a blocking synchronous network call. A slow (or
    hung) call must not freeze the whole worker process — regression test for a
    bug where a stuck embeddings call froze every other queued job."""
    monkeypatch.setattr(matcher.settings, "gemini_api_key", "k")
    monkeypatch.setattr(matcher, "compute_bm25_score", lambda jd, resume: 0.5)

    def slow_sync_call(jd, resume):
        time.sleep(0.2)
        return 0.5

    monkeypatch.setattr(matcher, "compute_semantic_score", slow_sync_call)

    async def fake_generate(prompt, *, gemini_model, groq_model):
        return '{"score": 0.9, "gap_analysis": "", "reasoning": ""}'

    monkeypatch.setattr(matcher, "generate", fake_generate)

    ticks = 0

    async def ticker():
        nonlocal ticks
        while True:
            ticks += 1
            await asyncio.sleep(0.02)

    ticker_task = asyncio.create_task(ticker())
    await matcher.compute_match("jd text", "resume text", "AI Engineer")
    ticker_task.cancel()

    # If compute_semantic_score blocked the event loop for its full 0.2s
    # duration, the ticker (waking every 0.02s) would get essentially zero
    # ticks in. A healthy offload lets it tick several times concurrently.
    assert ticks >= 5
