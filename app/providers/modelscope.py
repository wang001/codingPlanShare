import httpx
from typing import Dict, Any, AsyncGenerator
from app.providers.base import BaseProvider

# 单个请求超时：连接 10s，读取 120s（大模型响应慢）
_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=5.0)


class VendorResponseError(Exception):
    """
    厂商返回 HTTP 200，但响应体解析失败（格式非法/字段缺失）。
    此类异常视为"厂商已消耗算力"，调用方应照常扣积分。
    区别于 httpx.HTTPStatusError（HTTP 层面失败，不扣积分）。
    """


class ModelScopeProvider(BaseProvider):
    """
    通用 OpenAI 兼容厂商适配器（httpx 异步版）。
    适用于 ModelScope、智谱、MiniMax、DeepSeek、SiliconFlow 等所有 OpenAI 兼容接口。

    异常语义：
      - httpx.HTTPStatusError  : HTTP 层面失败（4xx/5xx），不扣积分
      - httpx.TimeoutException : 超时，不扣积分
      - VendorResponseError    : HTTP 200 但响应体解析失败，应扣积分
    """

    def __init__(self, api_key: str, base_url: str = "https://api-inference.modelscope.cn/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def chat_completion(self, model: str, messages: list, **kwargs) -> Dict[str, Any]:
        """
        聊天完成（非流式）。
        HTTP 错误直接抛 httpx.HTTPStatusError（不扣积分）。
        200 但解析失败抛 VendorResponseError（应扣积分，厂商已消耗算力）。
        """
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000),
        }
        async with httpx.AsyncClient(headers=self.headers, timeout=_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()  # 4xx/5xx → httpx.HTTPStatusError
            try:
                return response.json()
            except Exception as e:
                raise VendorResponseError(f"响应体解析失败: {e}，原始内容: {response.text[:200]}")

    async def chat_completion_stream(
        self, model: str, messages: list, **kwargs
    ) -> AsyncGenerator[str, None]:
        """聊天完成（流式 SSE）"""
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000),
            "stream": True,
        }
        async with httpx.AsyncClient(headers=self.headers, timeout=_TIMEOUT) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for chunk in response.aiter_text():
                    if chunk:
                        yield chunk

    async def embeddings(self, model: str, input: str, **kwargs) -> Dict[str, Any]:
        """嵌入接口"""
        url = f"{self.base_url}/embeddings"
        payload = {"model": model, "input": input}
        async with httpx.AsyncClient(headers=self.headers, timeout=_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
