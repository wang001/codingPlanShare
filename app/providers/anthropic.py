import json
import time
from typing import Any, AsyncGenerator, Dict, List, Tuple

import httpx

from app.providers.base import BaseProvider
from app.providers.modelscope import VendorResponseError

_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=5.0)
_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(BaseProvider):
    """Anthropic Messages API adapter that returns OpenAI-compatible responses."""

    def __init__(self, api_key: str, base_url: str = "https://api.anthropic.com/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

    async def chat_completion(self, model: str, messages: list, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}/messages"
        payload = self._build_payload(model, messages, kwargs, stream=False)

        async with httpx.AsyncClient(headers=self.headers, timeout=_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            try:
                data = response.json()
            except Exception as e:
                raise VendorResponseError(f"响应体解析失败: {e}，原始内容: {response.text[:200]}")

        return self._normalize_response(data, model)

    async def chat_completion_stream(
        self, model: str, messages: list, **kwargs
    ) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/messages"
        payload = self._build_payload(model, messages, kwargs, stream=True)

        async with httpx.AsyncClient(headers=self.headers, timeout=_TIMEOUT) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line.removeprefix("data:").strip()
                    if not raw or raw == "[DONE]":
                        continue
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    chunk = self._normalize_stream_event(event, model)
                    if chunk:
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"

    async def embeddings(self, model: str, input: str, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError("Anthropic Messages API 不支持 embeddings")

    @staticmethod
    def _build_payload(model: str, messages: list, kwargs: Dict[str, Any], stream: bool) -> Dict[str, Any]:
        system, user_messages = AnthropicProvider._split_system_messages(messages)
        payload: Dict[str, Any] = {
            "model": model,
            "messages": user_messages,
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.7),
        }
        if system:
            payload["system"] = system
        if stream:
            payload["stream"] = True
        return payload

    @staticmethod
    def _split_system_messages(messages: list) -> Tuple[str, List[Dict[str, Any]]]:
        system_parts: List[str] = []
        user_messages: List[Dict[str, Any]] = []
        for message in messages:
            role = message.get("role")
            content = message.get("content", "")
            if role == "system":
                system_parts.append(AnthropicProvider._content_to_text(content))
            elif role in {"user", "assistant"}:
                user_messages.append({"role": role, "content": content})
        return "\n\n".join(part for part in system_parts if part), user_messages

    @staticmethod
    def _content_to_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(str(block.get("text", "")))
            return "\n".join(part for part in text_parts if part)
        return str(content)

    @staticmethod
    def _normalize_response(data: Dict[str, Any], requested_model: str) -> Dict[str, Any]:
        content = ""
        for block in data.get("content", []):
            if isinstance(block, dict) and block.get("type") == "text":
                content += block.get("text", "")

        usage = data.get("usage") or {}
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        return {
            "id": data.get("id", f"anthropic-{int(time.time())}"),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": data.get("model", requested_model),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": AnthropicProvider._map_stop_reason(data.get("stop_reason")),
                }
            ],
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
        }

    @staticmethod
    def _normalize_stream_event(event: Dict[str, Any], requested_model: str) -> Dict[str, Any] | None:
        event_type = event.get("type")
        if event_type == "content_block_delta":
            delta = event.get("delta") or {}
            text = delta.get("text")
            if text is None:
                return None
            return {
                "id": event.get("message_id", f"anthropic-{int(time.time())}"),
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": requested_model,
                "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}],
            }
        if event_type == "message_stop":
            return {
                "id": event.get("message_id", f"anthropic-{int(time.time())}"),
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": requested_model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
        return None

    @staticmethod
    def _map_stop_reason(reason: str | None) -> str | None:
        if reason == "end_turn":
            return "stop"
        if reason == "max_tokens":
            return "length"
        return reason
