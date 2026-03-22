import secrets
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.api_key import ApiKey
from app.utils.encryption import encrypt_data, decrypt_data
from app.utils.cache import cache

class KeyService:
    @staticmethod
    def generate_api_key() -> str:
        """生成API密钥"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def create_api_key(db: Session, user_id: int, key_type: int, name: str, provider: Optional[str] = None, raw_key: Optional[str] = None) -> ApiKey:
        """创建API密钥"""
        if key_type == 2 and not provider:
            raise ValueError("厂商密钥必须指定厂商类型")
        
        if key_type == 2 and not raw_key:
            raise ValueError("厂商密钥必须提供原始密钥")
        
        # 生成或加密密钥
        if key_type == 1:
            # 平台调用密钥，直接使用生成的密钥
            encrypted_key = KeyService.generate_api_key()
        else:
            # 厂商密钥，需要加密存储
            encrypted_key = encrypt_data(raw_key)
        
        api_key = ApiKey(
            user_id=user_id,
            key_type=key_type,
            provider=provider,
            encrypted_key=encrypted_key,
            name=name,
            status=0
        )
        db.add(api_key)
        db.commit()
        db.refresh(api_key)
        return api_key

    @staticmethod
    def get_user_keys(db: Session, user_id: int, key_type: Optional[int] = None) -> List[ApiKey]:
        """获取用户的API密钥列表"""
        query = db.query(ApiKey).filter(ApiKey.user_id == user_id)
        if key_type is not None:
            query = query.filter(ApiKey.key_type == key_type)
        return query.filter(ApiKey.status != 1).all()

    @staticmethod
    def get_key_by_id(db: Session, key_id: int) -> Optional[ApiKey]:
        """通过ID获取API密钥"""
        return db.query(ApiKey).filter(ApiKey.id == key_id).first()

    @staticmethod
    def get_key_by_value(db: Session, key_value: str) -> Optional[ApiKey]:
        """通过密钥值获取API密钥"""
        # 尝试从缓存获取
        cache_key = f"api_key:{key_value}"
        cached_key = cache.get(cache_key)
        if cached_key is not None:
            return cached_key
        
        # 从数据库获取
        key = db.query(ApiKey).filter(ApiKey.encrypted_key == key_value).first()
        
        # 缓存结果
        if key:
            cache.set(cache_key, key, expire_seconds=3600)  # 缓存1小时
        return key

    @staticmethod
    def get_available_provider_keys(db: Session, provider: str) -> List[ApiKey]:
        """获取可用的厂商密钥"""
        # 尝试从缓存获取
        cache_key = f"available_keys:{provider}"
        cached_keys = cache.get(cache_key)
        if cached_keys is not None:
            return cached_keys
        
        # 从数据库获取
        keys = db.query(ApiKey).filter(
            ApiKey.key_type == 2,
            ApiKey.provider == provider,
            ApiKey.status == 0
        ).all()
        
        # 缓存结果
        cache.set(cache_key, keys, expire_seconds=300)  # 缓存5分钟
        return keys

    @staticmethod
    def update_key_status(db: Session, key_id: int, status: int):
        """更新密钥状态"""
        key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
        if key:
            key.status = status
            db.commit()
            
            # 清除缓存
            if key.encrypted_key:
                cache_key = f"api_key:{key.encrypted_key}"
                cache.delete(cache_key)
            if key.provider:
                cache_key = f"available_keys:{key.provider}"
                cache.delete(cache_key)

    @staticmethod
    def update_key_usage(db: Session, key_id: int):
        """更新密钥使用情况"""
        import time
        key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
        if key:
            key.used_count += 1
            key.last_used_at = int(time.time())
            db.commit()

    @staticmethod
    def decrypt_provider_key(encrypted_key: str) -> str:
        """解密厂商密钥"""
        return decrypt_data(encrypted_key)