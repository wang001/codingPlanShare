import requests
import asyncio
from typing import Dict, Any, AsyncGenerator
from app.providers.base import BaseProvider

class ModelScopeProvider(BaseProvider):
    """ModelScope厂商适配器"""
    
    def __init__(self, api_key: str, base_url: str = "https://api-inference.modelscope.cn/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def chat_completion(self, model: str, messages: list, **kwargs) -> Dict[str, Any]:
        """聊天完成接口"""
        url = f"{self.base_url}/chat/completions"
        data = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000)
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
    
    async def chat_completion_stream(self, model: str, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        """聊天完成接口（流式）"""
        url = f"{self.base_url}/chat/completions"
        data = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000),
            "stream": True
        }
        
        with requests.post(url, headers=self.headers, json=data, stream=True) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                if chunk:
                    yield chunk
    
    def embeddings(self, model: str, input: str, **kwargs) -> Dict[str, Any]:
        """嵌入接口"""
        url = f"{self.base_url}/embeddings"
        data = {
            "model": model,
            "input": input
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
