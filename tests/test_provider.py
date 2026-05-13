import asyncio

from app.providers.modelscope import ModelScopeProvider


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.text = str(payload)
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeAsyncClient:
    requests = []

    def __init__(self, headers=None, timeout=None):
        self.headers = headers
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url, json):
        self.requests.append({"url": url, "json": json, "headers": self.headers})
        if url.endswith("/chat/completions"):
            return FakeResponse(
                {
                    "id": "chatcmpl-test",
                    "object": "chat.completion",
                    "created": 1700000000,
                    "model": json["model"],
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "ok"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                }
            )
        if url.endswith("/embeddings"):
            return FakeResponse({"object": "list", "data": [{"embedding": [0.1, 0.2]}]})
        if url.endswith("/responses"):
            return FakeResponse({"id": "resp-test", "object": "response", "model": json["model"]})
        raise AssertionError(f"unexpected url: {url}")


def test_modelscope_provider_chat_completion_uses_openai_compatible_payload(monkeypatch):
    FakeAsyncClient.requests = []
    monkeypatch.setattr("app.providers.modelscope.httpx.AsyncClient", FakeAsyncClient)

    provider = ModelScopeProvider("test-key", base_url="https://example.com/v1")
    response = asyncio.run(
        provider.chat_completion(
            model="qwen-test",
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.2,
            max_tokens=128,
        )
    )

    assert response["id"] == "chatcmpl-test"
    request = FakeAsyncClient.requests[0]
    assert request["url"] == "https://example.com/v1/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer test-key"
    assert request["json"] == {
        "model": "qwen-test",
        "messages": [{"role": "user", "content": "hi"}],
        "temperature": 0.2,
        "max_tokens": 128,
    }


def test_modelscope_provider_embeddings(monkeypatch):
    FakeAsyncClient.requests = []
    monkeypatch.setattr("app.providers.modelscope.httpx.AsyncClient", FakeAsyncClient)

    provider = ModelScopeProvider("test-key", base_url="https://example.com/v1")
    response = asyncio.run(provider.embeddings(model="embedding-test", input="hello"))

    assert response["data"][0]["embedding"] == [0.1, 0.2]
    request = FakeAsyncClient.requests[0]
    assert request["url"] == "https://example.com/v1/embeddings"
    assert request["json"] == {"model": "embedding-test", "input": "hello"}


def test_modelscope_provider_responses_passthrough(monkeypatch):
    FakeAsyncClient.requests = []
    monkeypatch.setattr("app.providers.modelscope.httpx.AsyncClient", FakeAsyncClient)

    provider = ModelScopeProvider("test-key", base_url="https://example.com/v1")
    response = asyncio.run(provider.responses({"model": "gpt-test", "input": "hello"}))

    assert response["id"] == "resp-test"
    request = FakeAsyncClient.requests[0]
    assert request["url"] == "https://example.com/v1/responses"
    assert request["json"] == {"model": "gpt-test", "input": "hello"}
