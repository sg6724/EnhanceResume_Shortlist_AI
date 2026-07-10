from __future__ import annotations

from typing import Any, Callable


class GeminiClient:
    """Wraps google-genai behind the LlmClient protocol.

    Caches ONE underlying `genai.Client` instance for the lifetime of this
    object. Creating a fresh `genai.Client()` per call was the root cause of a
    previously-diagnosed bug: the garbage-collected temporary client closed a
    shared httpx transport, breaking the next call with "RuntimeError: Cannot
    send a request, as the client has been closed." A single long-lived
    client, plus the async `.aio` surface for `generate`, avoids this.
    """

    def __init__(self, api_key: str, client_factory: Callable[[], Any] | None = None):
        self._api_key = api_key
        if client_factory is not None:
            self._client_factory = client_factory
        else:
            def _default_factory():
                from google import genai
                return genai.Client(api_key=self._api_key)
            self._client_factory = _default_factory
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    async def generate(self, model: str, prompt: str) -> str:
        resp = await self._get_client().aio.models.generate_content(model=model, contents=prompt)
        return resp.text

    def embed(self, model: str, text: str) -> list[float]:
        result = self._get_client().models.embed_content(model=model, contents=text[:2048])
        return result.embeddings[0].values
