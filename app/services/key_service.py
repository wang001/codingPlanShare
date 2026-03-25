import secrets
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.api_key import ApiKey
from app.utils.encryption import encrypt_data, decrypt_data
from app.utils.cache import cache

logger = logging.getLogger(__name__)

# 超限冷却时长（秒）
RATE_LIMIT_COOLDOWN_SECONDS = 3600  # 1 小时


class KeyService:
    @staticmethod
    def generate_api_key() -> str:
        """生成API密钥"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def create_api_key(
        db: Session,
        user_id: int,
        key_type: int,
        name: str,
        provider: Optional[str] = None,
        raw_key: Optional[str] = None,
    ) -> ApiKey:
        """创建API密钥"""
        if key_type == 2 and not provider:
            raise ValueError("厂商密钥必须指定厂商类型")

        if key_type == 2 and not raw_key:
            raise ValueError("厂商密钥必须提供原始密钥")

        # provider 白名单校验（防止写入非法厂商，与路由层保持一致）
        if key_type == 2 and provider:
            from app.services.router_service import RouterService
            if not RouterService.is_provider_allowed(provider):
                raise ValueError(f"不支持的厂商: {provider}，请联系管理员")

        # 生成或加密密钥
        if key_type == 1:
            encrypted_key = KeyService.generate_api_key()
        else:
            encrypted_key = encrypt_data(raw_key)

        api_key = ApiKey(
            user_id=user_id,
            key_type=key_type,
            provider=provider,
            encrypted_key=encrypted_key,
            name=name,
            status=0,
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
    def get_key_by_value(db: Session, key_value: str):
        """
        通过密钥值获取API密钥。
        缓存层存 plain dict（避免 session 关闭后 DetachedInstanceError），
        返回 SimpleNamespace，字段访问方式与 ApiKey ORM 对象一致。
        """
        cache_key = f"api_key:{key_value}"
        cached = cache.get(cache_key)
        if cached is not None:
            return KeyService._dict_to_key(cached)

        key = db.query(ApiKey).filter(ApiKey.encrypted_key == key_value).first()
        if key:
            cache.set(cache_key, KeyService._key_to_dict(key), expire_seconds=3600)
            return key  # 首次从 DB 查到，直接返回 ORM 对象（session 仍开着，安全）
        return None

    @staticmethod
    def _lazy_recover_cooldown(db: Session, key: ApiKey) -> bool:
        """
        懒恢复：如果 key 的 cooldown_until 非 null 且已过期，清除冷却标记。
        冷却状态由 status=0 + cooldown_until 共同表达，status 本身不变。
        返回 True 表示已恢复（冷却过期），False 表示仍在冷却中或无冷却。
        """
        if key.cooldown_until is None:
            return False

        now = datetime.now(timezone.utc)
        # cooldown_until 可能是 naive datetime（SQLite 无时区），统一转为 UTC 比较
        cooldown = key.cooldown_until
        if cooldown.tzinfo is None:
            cooldown = cooldown.replace(tzinfo=timezone.utc)

        if now >= cooldown:
            # 冷却已过期，清除 cooldown_until，不修改 status
            key.cooldown_until = None
            db.commit()
            if key.provider:
                cache.delete(f"available_keys:{key.provider}")
            logger.info(f"[KeyService] key_id={key.id} 冷却已过期，已恢复为可用")
            return True
        return False

    @staticmethod
    def _key_to_dict(key: ApiKey) -> dict:
        """将 ApiKey ORM 对象序列化为 plain dict，用于安全缓存（避免 DetachedInstanceError）。"""
        return {
            "id":            key.id,
            "user_id":       key.user_id,
            "key_type":      key.key_type,
            "provider":      key.provider,
            "encrypted_key": key.encrypted_key,
            "name":          key.name,
            "status":        key.status,
            "used_count":    key.used_count,
            "last_used_at":  key.last_used_at,
            "created_at":    key.created_at,
        }

    @staticmethod
    def _dict_to_key(d: dict):
        """
        将 plain dict 还原为轻量对象（types.SimpleNamespace），字段访问方式与 ApiKey 完全一致。
        不绑定 session，不会触发 DetachedInstanceError，仅用于读取字段（id/key_type/encrypted_key 等）。
        """
        from types import SimpleNamespace
        return SimpleNamespace(**d)

    @staticmethod
    def get_available_provider_keys(db: Session, provider: str) -> List[ApiKey]:
        """
        获取可用的厂商密钥。
        可用条件：status=0 且（cooldown_until 为 null 或已过期）。
        冷却到期的 key 在此处懒恢复（清除 cooldown_until）。
        结果缓存 5 分钟（存 plain dict，避免 DetachedInstanceError）。
        """
        cache_key = f"available_keys:{provider}"
        cached = cache.get(cache_key)
        if cached is not None:
            return [KeyService._dict_to_key(d) for d in cached]

        all_keys = db.query(ApiKey).filter(
            ApiKey.key_type == 2,
            ApiKey.provider == provider,
            ApiKey.status == 0,
        ).all()

        available = []
        for key in all_keys:
            if key.cooldown_until is None:
                available.append(key)
            else:
                recovered = KeyService._lazy_recover_cooldown(db, key)
                if recovered:
                    available.append(key)

        # 序列化为 plain dict 再缓存，防止 session 关闭后 ORM 对象失效
        cache.set(cache_key, [KeyService._key_to_dict(k) for k in available], expire_seconds=300)
        return available

    @staticmethod
    def mark_key_rate_limited(db: Session, key_id: int):
        """
        标记厂商密钥遭遇 429/rate limit。
        只写 cooldown_until = now + 1h，status 保持 0 不变。
        冷却状态由 status=0 + cooldown_until 共同表达，过期后懒恢复（清除 cooldown_until）。
        """
        key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
        if not key:
            return
        cooldown_until = datetime.now(timezone.utc) + timedelta(seconds=RATE_LIMIT_COOLDOWN_SECONDS)
        key.cooldown_until = cooldown_until
        db.commit()

        if key.provider:
            cache.delete(f"available_keys:{key.provider}")
        logger.warning(
            f"[KeyService] key_id={key.id} 遭遇超限，冷却至 {cooldown_until.isoformat()}"
        )

    @staticmethod
    def mark_key_invalid(db: Session, key_id: int):
        """
        标记厂商密钥为无效（status=4）。
        用于 401/403 等认证失败场景，需人工更换密钥。
        """
        key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
        if not key:
            return
        key.status = 4
        key.cooldown_until = None
        db.commit()

        if key.provider:
            cache.delete(f"available_keys:{key.provider}")
        logger.warning(f"[KeyService] key_id={key.id} 认证失败，已标记为无效（status=4）")

    @staticmethod
    def update_key_status(db: Session, key_id: int, status: int):
        """更新密钥状态"""
        key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
        if key:
            key.status = status
            db.commit()

            if key.encrypted_key:
                cache.delete(f"api_key:{key.encrypted_key}")
            if key.provider:
                cache.delete(f"available_keys:{key.provider}")

    @staticmethod
    def update_key_usage(db: Session, key_id: int):
        """更新密钥使用情况"""
        key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
        if key:
            key.used_count += 1
            key.last_used_at = int(time.time())
            db.commit()

    @staticmethod
    def decrypt_provider_key(encrypted_key: str) -> str:
        """解密厂商密钥"""
        return decrypt_data(encrypted_key)
