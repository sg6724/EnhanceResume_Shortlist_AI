from app.integrations.llm.gemini import GeminiClient


class _FakeAioModels:
    def __init__(self, response_text: str):
        self._response_text = response_text
        self.calls: list[tuple[str, str]] = []

    async def generate_content(self, model: str, contents: str):
        self.calls.append((model, contents))
        class _Resp:
            text = self._response_text
        return _Resp()


class _FakeAio:
    def __init__(self, response_text: str):
        self.models = _FakeAioModels(response_text)


class _FakeSyncModels:
    def __init__(self, vector: list[float]):
        self._vector = vector
        self.calls: list[tuple[str, str]] = []

    def embed_content(self, model: str, contents: str):
        self.calls.append((model, contents))
        class _Embedding:
            values = self._vector
        class _Result:
            embeddings = [_Embedding()]
        return _Result()


class _FakeGenaiClient:
    def __init__(self, response_text="OK", vector=None):
        self.aio = _FakeAio(response_text)
        self.models = _FakeSyncModels(vector or [0.1, 0.2, 0.3])


async def test_generate_delegates_to_async_client_and_returns_text():
    fake = _FakeGenaiClient(response_text="hello world")
    client = GeminiClient(api_key="test-key", client_factory=lambda: fake)
    result = await client.generate("gemini-2.5-flash", "say hi")
    assert result == "hello world"
    assert fake.aio.models.calls == [("gemini-2.5-flash", "say hi")]


def test_embed_delegates_to_sync_client_and_returns_vector():
    fake = _FakeGenaiClient(vector=[1.0, 2.0])
    client = GeminiClient(api_key="test-key", client_factory=lambda: fake)
    result = client.embed("gemini-embedding-001", "some resume text")
    assert result == [1.0, 2.0]


async def test_client_factory_called_at_most_once():
    calls = {"n": 0}
    fake = _FakeGenaiClient()

    def factory():
        calls["n"] += 1
        return fake

    client = GeminiClient(api_key="test-key", client_factory=factory)
    client.embed("gemini-embedding-001", "text one")
    await client.generate("gemini-2.5-flash", "prompt two")
    client.embed("gemini-embedding-001", "text three")
    assert calls["n"] == 1
