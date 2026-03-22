from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.point_log import PointLog
from app.utils.cache import cache

class PointsService:
    @staticmethod
    def get_user_balance(db: Session, user_id: int) -> int:
        """获取用户积分余额"""
        # 尝试从缓存获取
        cache_key = f"user:balance:{user_id}"
        cached_balance = cache.get(cache_key)
        if cached_balance is not None:
            return cached_balance
        
        # 从数据库获取
        user = db.query(User).filter(User.id == user_id).first()
        balance = user.balance if user else 0
        
        # 缓存结果
        cache.set(cache_key, balance, expire_seconds=3600)  # 缓存1小时
        return balance

    @staticmethod
    def pre_deduct_points(db: Session, user_id: int, amount: int) -> bool:
        """预扣积分"""
        # 先从缓存获取当前余额
        current_balance = PointsService.get_user_balance(db, user_id)
        if current_balance < amount:
            return False
        
        # 更新缓存
        new_balance = current_balance - amount
        cache_key = f"user:balance:{user_id}"
        cache.set(cache_key, new_balance, expire_seconds=3600)
        return True

    @staticmethod
    def confirm_deduct(db: Session, user_id: int, amount: int, log_type: int, related_key_id: Optional[int] = None, model: Optional[str] = None, remark: Optional[str] = None):
        """确认扣费并记录日志"""
        # 记录积分变动日志
        point_log = PointLog(
            user_id=user_id,
            amount=-amount,
            type=log_type,
            related_key_id=related_key_id,
            model=model,
            remark=remark
        )
        db.add(point_log)
        db.commit()

    @staticmethod
    def rollback_points(db: Session, user_id: int, amount: int):
        """回滚积分"""
        # 从缓存获取当前余额
        current_balance = PointsService.get_user_balance(db, user_id)
        
        # 更新缓存
        new_balance = current_balance + amount
        cache_key = f"user:balance:{user_id}"
        cache.set(cache_key, new_balance, expire_seconds=3600)

    @staticmethod
    def add_points(db: Session, user_id: int, amount: int, log_type: int, related_key_id: Optional[int] = None, model: Optional[str] = None, remark: Optional[str] = None):
        """增加积分"""
        # 从缓存获取当前余额
        current_balance = PointsService.get_user_balance(db, user_id)
        
        # 更新缓存
        new_balance = current_balance + amount
        cache_key = f"user:balance:{user_id}"
        cache.set(cache_key, new_balance, expire_seconds=3600)
        
        # 记录积分变动日志
        point_log = PointLog(
            user_id=user_id,
            amount=amount,
            type=log_type,
            related_key_id=related_key_id,
            model=model,
            remark=remark
        )
        db.add(point_log)
        db.commit()

    @staticmethod
    def get_point_logs(db: Session, user_id: int, limit: int = 100, offset: int = 0):
        """获取积分明细"""
        return db.query(PointLog).filter(PointLog.user_id == user_id).order_by(PointLog.created_at.desc()).limit(limit).offset(offset).all()