from __future__ import annotations

import pytest

from app.agents import rewriter

MASTER_TEX = r"\documentclass{article}\begin{document}Hello\end{document}"


async def test_rewrite_returns_tex_and_diff_when_generate_succeeds(monkeypatch):
    monkeypatch.setattr(rewriter.settings, "gemini_api_key", "k")

    async def fake_generate(prompt, *, gemini_model, groq_model):
        return (
            r"\documentclass{article}\begin{document}Hi there\end{document}"
            "\nDIFF:\n- changed greeting"
        )

    monkeypatch.setattr(rewriter, "generate", fake_generate)

    tex, diff = await rewriter.rewrite_resume(MASTER_TEX, "jd text", "gap analysis", "AI Engineer")
    assert "Hi there" in tex
    assert diff.startswith("DIFF:")


async def test_rewrite_raises_when_generate_raises(monkeypatch):
    monkeypatch.setattr(rewriter.settings, "gemini_api_key", "k")

    async def fake_generate(prompt, *, gemini_model, groq_model):
        raise RuntimeError("no LLM provider available")

    monkeypatch.setattr(rewriter, "generate", fake_generate)

    with pytest.raises(RuntimeError):
        await rewriter.rewrite_resume(MASTER_TEX, "jd text", "gap analysis", "AI Engineer")


async def test_no_keys_configured_returns_master_unchanged(monkeypatch):
    monkeypatch.setattr(rewriter.settings, "gemini_api_key", "")
    monkeypatch.setattr(rewriter.settings, "groq_api_key", "")

    tex, diff = await rewriter.rewrite_resume(MASTER_TEX, "jd text", "gap analysis", "AI Engineer")
    assert tex == MASTER_TEX
    assert "GEMINI_API_KEY" in diff


async def test_strips_conversational_preamble_before_documentclass(monkeypatch):
    """The model sometimes prefaces the tex with prose instead of returning
    only the file, which breaks pdflatex ('Missing \\begin{document}') even
    though the environment-structure check still passes."""
    monkeypatch.setattr(rewriter.settings, "gemini_api_key", "k")

    async def fake_generate(prompt, *, gemini_model, groq_model):
        return (
            "Here is the modified LaTeX resume for the position:\n"
            r"\documentclass{article}\begin{document}Hi there\end{document}"
            "\nDIFF:\n- changed greeting"
        )

    monkeypatch.setattr(rewriter, "generate", fake_generate)

    tex, diff = await rewriter.rewrite_resume(MASTER_TEX, "jd text", "gap analysis", "AI Engineer")
    assert tex.startswith(r"\documentclass")
