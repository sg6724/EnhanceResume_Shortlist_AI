from __future__ import annotations

from google import genai
from groq import AsyncGroq

from ..config import settings

# A SINGLE, process-wide genai client, created lazily and cached.
#
# Why a singleton: the google-genai SDK keeps a shared httpx transport. Creating a
# fresh `genai.Client()` per call (the old pattern) means each temporary client is
# garbage-collected after the call, and its __del__ closes that shared transport —
# so the *next* call fails with "RuntimeError: Cannot send a request, as the client
# has been closed." Reusing one long-lived client avoids the GC-triggered close.
#
# Bind-to-loop note: the async transport (`client.aio`) is bound to the event loop
# that first uses it. The API and worker are separate processes, each with one
# stable asyncio loop, so a per-process singleton is safe.
_client: genai.Client | None = None
_groq_client: AsyncGroq | None = None


def get_client() -> genai.Client:
    """Return the shared genai client (creates it on first use).

    Without an explicit timeout, a hung TCP handshake (observed here as an
    IPv6 SYN that never completes) blocks forever — and since embeddings
    calls run synchronously on the worker's single event loop thread, that
    hang freezes every other queued job too. 30s is generous for a single
    embed/generate call but still bounded.
    """
    global _client
    if _client is None:
        _client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=genai.types.HttpOptions(timeout=30_000),
        )
    return _client


def get_groq_client() -> AsyncGroq:
    """Return the shared Groq client (creates it on first use). Same singleton
    rationale as get_client(): reuse one long-lived async client per process
    rather than one per call."""
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncGroq(api_key=settings.groq_api_key)
    return _groq_client


async def generate(prompt: str, *, gemini_model: str, groq_model: str) -> str:
    """Try Gemini first; fall back to Groq on any failure or missing key.
    Raises RuntimeError only when both providers are unconfigured or both
    fail. Every existing call site catches bare `Exception`, so this new
    exception type is transparent to current error handling."""
    errors: list[str] = []

    if settings.gemini_api_key:
        try:
            resp = await get_client().aio.models.generate_content(model=gemini_model, contents=prompt)
            return resp.text or ""
        except Exception as e:
            errors.append(f"gemini: {e}")
    else:
        errors.append("gemini: no GEMINI_API_KEY")

    if settings.groq_api_key:
        try:
            resp = await get_groq_client().chat.completions.create(
                model=groq_model,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            errors.append(f"groq: {e}")
    else:
        errors.append("groq: no GROQ_API_KEY")

    raise RuntimeError(f"no LLM provider available — {'; '.join(errors)}")
