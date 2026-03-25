"""
Mock 厂商适配器
===============

用于本地开发和测试，无需真实 API Key，无限流限制。

特性：
  - 立即返回，延迟可配置（模拟网络耗时）
  - 支持模拟失败（fail_rate 控制失败概率）
  - token 计数和真实响应格式完全一致
  - 支持流式响应

使用方式：
  在数据库中创建厂商密钥时，provider 填 "mock"，encrypted_key 可以是任意字符串。
  调用时 model 填 "mock/any-model-name"。

Mock key 格式（可选，用于控制行为）：
  "mock"              → 正常响应
  "mock:slow"         → 模拟慢响应（2秒延迟）
  "mock:fail"         → 总是失败
  "mock:fail_rate=0.3"→ 30% 概率失败
"""

import time
import json
import random
import asyncio
from typing import Dict, Any, AsyncGenerator
from app.providers.base import BaseProvider

# mock 回复池，随机选一条返回
_MOCK_REPLIES = [
    "这是一条来自 Mock Provider 的测试回复。",
    "Mock response: 系统运行正常，积分计费逻辑已验证。",
    "Hello from Mock! 你的请求已被成功处理。",
    "测试通过 ✅ Mock Provider 响应正常。",
    "这是模拟的 LLM 响应，用于本地开发和并发测试。",
]


class MockProvider(BaseProvider):
    """
    Mock 厂商适配器，用于测试和开发。
    api_key 格式决定行为：
      "mock"              → 正常，即时响应
      "mock:slow"         → 正常，但延迟 2 秒
      "mock:fail"         → 总是返回错误
      "mock:fail_rate=N"  → N 概率失败（0.0~1.0）
    """

    def __init__(self, api_key: str = "mock", base_url: str = ""):
        self.api_key = api_key
        self._parse_behavior(api_key)

    def _parse_behavior(self, key: str):
        self.delay = 0.0
        self.always_fail = False
        self.fail_rate = 0.0

        parts = key.lower().split(":")
        if len(parts) < 2:
            return
        directive = parts[1]

        if directive == "slow":
            self.delay = 2.0
        elif directive == "fail":
            self.always_fail = True
        elif directive.startswith("fail_rate="):
            try:
                self.fail_rate = float(directive.split("=")[1])
            except ValueError:
                pass

    def _should_fail(self) -> bool:
        if self.always_fail:
            return True
        if self.fail_rate > 0:
            return random.random() < self.fail_rate
        return False

    def _make_response(self, model: str, content: str, prompt_tokens: int) -> Dict[str, Any]:
        completion_tokens = len(content.split())
        return {
            "id": f"chatcmpl-mock-{int(time.time() * 1000)}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }

    async def chat_completion(self, model: str, messages: list, **kwargs) -> Dict[str, Any]:
        if self.delay:
            await asyncio.sleep(self.delay)

        if self._should_fail():
            raise Exception("Mock provider simulated failure")

        prompt_tokens = sum(len(str(m.get("content", ""))) // 4 for m in messages)
        content = random.choice(_MOCK_REPLIES)
        return self._make_response(model, content, prompt_tokens)

    async def chat_completion_stream(
        self, model: str, messages: list, **kwargs
    ) -> AsyncGenerator[str, None]:
        if self.delay:
            await asyncio.sleep(self.delay)

        if self._should_fail():
            raise Exception("Mock provider simulated failure (stream)")

        prompt_tokens = sum(len(str(m.get("content", ""))) // 4 for m in messages)
        content = random.choice(_MOCK_REPLIES)
        response_id = f"chatcmpl-mock-{int(time.time() * 1000)}"
        created = int(time.time())

        # 逐词流式输出
        words = content.split()
        for i, word in enumerate(words):
            chunk = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": word + (" " if i < len(words) - 1 else "")},
                        "finish_reason": None,
                    }
                ],
            }
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)  # 模拟逐词延迟

        # 结束 chunk
        end_chunk = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": len(words),
                "total_tokens": prompt_tokens + len(words),
            },
        }
        yield f"data: {json.dumps(end_chunk, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    async def embeddings(self, model: str, input: str, **kwargs) -> Dict[str, Any]:
        """返回随机向量，维度 1536（兼容 OpenAI text-embedding-ada-002）"""
        vector = [random.uniform(-1, 1) for _ in range(1536)]
        return {
            "object": "list",
            "data": [{"object": "embedding", "index": 0, "embedding": vector}],
            "model": model,
            "usage": {"prompt_tokens": len(input) // 4, "total_tokens": len(input) // 4},
        }
