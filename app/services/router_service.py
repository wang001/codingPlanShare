from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.models.api_key import ApiKey
from app.services.key_service import KeyService
from app.utils.cache import cache
from app.config.settings import settings

# ============================================================
# 厂商白名单：provider 名称 → base_url
# 安全策略：只允许访问此处登记的已知厂商地址，防止 SSRF。
# 新增厂商时在此处添加，未登记的 provider 创建密钥时会被拒绝。
# ============================================================
PROVIDER_BASE_URLS: Dict[str, str] = {
    "modelscope": "https://api-inference.modelscope.cn/v1",
    "zhipu":      "https://open.bigmodel.cn/api/paas/v4",
    "minimax":    "https://api.minimax.chat/v1",
    "alibaba":    "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "tencent":    "https://api.hunyuan.cloud.tencent.com/v1",
    "baidu":      "https://qianfan.baidubce.com/v2",
    "deepseek":   "https://api.deepseek.com/v1",
    "siliconflow":"https://api.siliconflow.cn/v1",
    # mock provider：仅用于开发和测试，不发起真实网络请求
    "mock":       "http://mock.internal/v1",
}

class RouterService:
    @staticmethod
    def get_provider_from_model(model: str) -> tuple:
        """从模型名称获取厂商类型和实际模型名称"""
        # 只支持"provider/model"格式
        if '/' in model:
            # 在首个"/"处切分，确保模型名称中的"/"不被错误处理
            parts = model.split('/', 1)
            provider = parts[0].lower()
            actual_model = parts[1]
            return provider, actual_model
        else:
            # 如果不是"provider/model"格式，默认使用modelscope
            return 'modelscope', model

    @staticmethod
    def select_provider_key(db: Session, provider: str, exclude_key_id: Optional[int] = None) -> Optional[ApiKey]:
        """
        选择可用的厂商密钥。
        - 通过 KeyService.get_available_provider_keys 获取（含懒恢复逻辑）
        - 排除指定的 key（用于重试时跳过刚失败的 key）
        - 从可用列表中随机选一个（相比固定选最大 ID，避免单 key 热点）
        """
        import random
        available_keys = KeyService.get_available_provider_keys(db, provider)

        if exclude_key_id:
            available_keys = [k for k in available_keys if k.id != exclude_key_id]

        if not available_keys:
            return None

        return random.choice(available_keys)

    @staticmethod
    def route_request(db: Session, model: str, request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """路由请求到合适的厂商"""
        # 获取厂商类型和实际模型名称
        provider, actual_model = RouterService.get_provider_from_model(model)
        
        # 获取最大重试次数
        max_retry = settings.key_management.get('max_retry', 1)
        
        # 尝试使用不同的密钥
        excluded_key_ids = []
        for attempt in range(max_retry + 1):
            # 选择可用的厂商密钥（排除之前失败的）
            provider_key = RouterService.select_provider_key(db, provider, exclude_key_id=excluded_key_ids[-1] if excluded_key_ids else None)
            if not provider_key:
                return None
            
            # 解密厂商密钥（只有厂商密钥需要解密）
            if provider_key.key_type == 2:
                try:
                    decrypted_key = KeyService.decrypt_provider_key(provider_key.encrypted_key)
                except Exception:
                    # 解密失败，尝试下一个密钥
                    excluded_key_ids.append(provider_key.id)
                    continue
            else:
                # 平台调用密钥不需要解密
                decrypted_key = provider_key.encrypted_key
            
            # 构建厂商请求数据
            provider_request = RouterService.adapt_request(provider, actual_model, request_data, decrypted_key)
            
            return {
                'provider': provider,
                'key_id': provider_key.id,
                'key': decrypted_key,
                'request': provider_request
            }
        
        return None

    @staticmethod
    def adapt_request(provider: str, model: str, request_data: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        """适配请求参数到厂商 API 格式（统一 OpenAI 兼容格式，base_url 从白名单取）"""
        return {
            'base_url': PROVIDER_BASE_URLS.get(provider.lower(), ""),
            'model': model,
            'messages': request_data.get('messages', []),
            'temperature': request_data.get('temperature', 0.7),
            'max_tokens': request_data.get('max_tokens', 1000),
            'api_key': api_key,
        }

    @staticmethod
    def is_provider_allowed(provider: str) -> bool:
        """检查 provider 是否在白名单中（安全校验，防止 SSRF）"""
        return provider.lower() in PROVIDER_BASE_URLS

    @staticmethod
    def create_provider_instance(provider: str, api_key: str) -> Optional[Any]:
        """创建厂商适配器实例。
        - mock：使用 MockProvider，不发起真实网络请求
        - 其他：使用 ModelScopeProvider（统一 OpenAI 兼容格式）
        """
        provider = provider.lower()
        base_url = PROVIDER_BASE_URLS.get(provider)
        if base_url is None:
            return None  # provider 不在白名单，拒绝

        if provider == "mock":
            from app.providers.mock import MockProvider
            return MockProvider(api_key=api_key)

        from app.providers.modelscope import ModelScopeProvider
        return ModelScopeProvider(api_key=api_key, base_url=base_url)

    @staticmethod
    def normalize_response(provider: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """标准化厂商响应"""
        # 根据不同厂商标准化响应
        if provider == 'minimax':
            # 适配Minimax响应
            return {
                'id': response.get('id', ''),
                'object': 'chat.completion',
                'created': response.get('created', 0),
                'model': response.get('model', ''),
                'choices': response.get('choices', []),
                'usage': response.get('usage', {})
            }
        elif provider == 'zhipu':
            # 适配智谱响应
            return {
                'id': response.get('id', ''),
                'object': 'chat.completion',
                'created': response.get('created', 0),
                'model': response.get('model', ''),
                'choices': response.get('choices', []),
                'usage': response.get('usage', {})
            }
        elif provider == 'alibaba':
            # 适配阿里响应
            return {
                'id': response.get('id', ''),
                'object': 'chat.completion',
                'created': response.get('created', 0),
                'model': response.get('model', ''),
                'choices': response.get('choices', []),
                'usage': response.get('usage', {})
            }
        elif provider == 'tencent':
            # 适配腾讯响应
            return {
                'id': response.get('id', ''),
                'object': 'chat.completion',
                'created': response.get('created', 0),
                'model': response.get('model', ''),
                'choices': response.get('choices', []),
                'usage': response.get('usage', {})
            }
        elif provider == 'baidu':
            # 适配百度响应
            return {
                'id': response.get('id', ''),
                'object': 'chat.completion',
                'created': response.get('created', 0),
                'model': response.get('model', ''),
                'choices': response.get('choices', []),
                'usage': response.get('usage', {})
            }
        else:
            # 默认标准化
            return response