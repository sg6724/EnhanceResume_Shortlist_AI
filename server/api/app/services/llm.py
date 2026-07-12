from __future__ import annotations

from google import genai

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


def get_client() -> genai.Client:
    """Return the shared genai client (creates it on first use)."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client
