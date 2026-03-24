from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator


class BaseProvider(ABC):
    """基础厂商适配器（全异步接口）"""

    @abstractmethod
    async def chat_completion(self, model: str, messages: list, **kwargs) -> Dict[str, Any]:
        """聊天完成接口"""
        pass

    @abstractmethod
    async def chat_completion_stream(self, model: str, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        """聊天完成接口（流式）"""
        pass

    @abstractmethod
    async def embeddings(self, model: str, input: str, **kwargs) -> Dict[str, Any]:
        """嵌入接口"""
        pass
