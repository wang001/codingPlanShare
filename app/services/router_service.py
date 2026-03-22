from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.models.api_key import ApiKey
from app.services.key_service import KeyService
from app.utils.cache import cache
from app.config.settings import settings

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
        """选择可用的厂商密钥"""
        # 尝试从缓存获取密钥ID列表
        cache_key = f"available_keys:{provider}"
        cached_key_ids = cache.get(cache_key)
        
        if cached_key_ids:
            # 从缓存中过滤掉要排除的密钥
            if exclude_key_id:
                cached_key_ids = [key_id for key_id in cached_key_ids if key_id != exclude_key_id]
            if cached_key_ids:
                # 从数据库获取完整对象
                key = db.query(ApiKey).filter(ApiKey.id == cached_key_ids[0]).first()
                if key and key.status == 0:
                    return key
        
        # 从数据库获取
        query = db.query(ApiKey).filter(
            ApiKey.key_type == 2,
            ApiKey.provider == provider,
            ApiKey.status == 0
        )
        
        if exclude_key_id:
            query = query.filter(ApiKey.id != exclude_key_id)
        
        available_keys = query.all()
        
        if not available_keys:
            return None
        
        # 选择最新创建的密钥（ID最大的）
        available_keys.sort(key=lambda x: x.id, reverse=True)
        selected_key = available_keys[0]
        
        # 缓存密钥ID列表
        if settings.cache.get('enabled', True):
            key_ids = [key.id for key in available_keys]
            cache.set(cache_key, key_ids, expire_seconds=300)  # 缓存5分钟
        
        return selected_key

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
        """适配请求参数到厂商API格式"""
        # 根据不同厂商适配参数
        if provider == 'minimax':
            return {
                'model': model,
                'messages': request_data.get('messages', []),
                'temperature': request_data.get('temperature', 0.7),
                'max_tokens': request_data.get('max_tokens', 1000),
                'api_key': api_key
            }
        elif provider == 'zhipu':
            return {
                'model': model,
                'messages': request_data.get('messages', []),
                'temperature': request_data.get('temperature', 0.7),
                'max_tokens': request_data.get('max_tokens', 1000),
                'api_key': api_key
            }
        elif provider == 'alibaba':
            return {
                'model': model,
                'messages': request_data.get('messages', []),
                'temperature': request_data.get('temperature', 0.7),
                'max_tokens': request_data.get('max_tokens', 1000),
                'api_key': api_key
            }
        elif provider == 'tencent':
            return {
                'model': model,
                'messages': request_data.get('messages', []),
                'temperature': request_data.get('temperature', 0.7),
                'max_tokens': request_data.get('max_tokens', 1000),
                'api_key': api_key
            }
        elif provider == 'baidu':
            return {
                'model': model,
                'messages': request_data.get('messages', []),
                'temperature': request_data.get('temperature', 0.7),
                'max_tokens': request_data.get('max_tokens', 1000),
                'api_key': api_key
            }
        elif provider == 'modelscope':
            return {
                'base_url': 'https://api-inference.modelscope.cn/v1',
                'model': model,
                'messages': request_data.get('messages', []),
                'temperature': request_data.get('temperature', 0.7),
                'max_tokens': request_data.get('max_tokens', 1000),
                'api_key': api_key
            }
        else:
            # 默认适配
            return {
                'model': model,
                'messages': request_data.get('messages', []),
                'temperature': request_data.get('temperature', 0.7),
                'max_tokens': request_data.get('max_tokens', 1000),
                'api_key': api_key
            }

    @staticmethod
    def create_provider_instance(provider: str, api_key: str) -> Optional[Any]:
        """创建厂商适配器实例"""
        if provider == 'modelscope':
            from app.providers.modelscope import ModelScopeProvider
            return ModelScopeProvider(api_key)
        # 可以添加其他厂商的适配器
        return None

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