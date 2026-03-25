"""
积分服务 - 双后端策略模式
==========================

架构说明：
  根据配置的数据库 driver，自动选择不同的积分后端实现：

  - SQLiteBackend（driver=sqlite）：
      内存余额（_balances）是唯一实时计算来源，启动时懒加载。
      per-user 锁保证同一用户读-改-写原子，不同用户完全并行。
      积分变动产生 PendingLog 入队，后台任务每秒 flush_to_db() 批量落库。
      适合单机开发/演示场景。

  - MySQLBackend（driver=mysql）：
      直接写数据库，利用 MySQL 行锁保证并发安全。
      UPDATE ... WHERE balance >= amount 原子扣减，affected_rows=0 即余额不足。
      AI 响应本身耗时数秒，DB 写入毫秒级，无需缓存层。
      flush_to_db() 为空操作，background_tasks 无感知。

  PointsService 只依赖 PointsBackend 接口，不感知 driver，调用方代码零改动。
"""

import threading
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, List

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.user import User
from app.models.point_log import PointLog
from app.db.database import SessionLocal
from app.config.settings import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# 内部数据结构（SQLite 后端专用）
# ─────────────────────────────────────────────

@dataclass
class PendingLog:
    """待落库的积分变动记录（SQLite 模式使用）"""
    user_id: int
    delta: int
    balance_after: int
    log_amount: int
    log_type: int
    related_key_id: Optional[int]
    model: Optional[str]
    remark: Optional[str]
    created_at: int


# ─────────────────────────────────────────────
# 抽象接口
# ─────────────────────────────────────────────

class PointsBackend(ABC):
    """积分后端抽象接口，所有操作均需实现。"""

    @abstractmethod
    def get_balance(self, db: Session, user_id: int) -> int:
        """获取用户当前积分余额。"""

    @abstractmethod
    def pre_deduct(self, db: Session, user_id: int, amount: int) -> bool:
        """
        预扣积分。
        返回 True 表示扣减成功，False 表示余额不足。
        """

    @abstractmethod
    def rollback(self, db: Session, user_id: int, amount: int):
        """回滚预扣的积分（厂商调用失败时调用）。"""

    @abstractmethod
    def confirm_deduct(
        self,
        db: Session,
        user_id: int,
        amount: int,
        log_type: int,
        related_key_id: Optional[int] = None,
        model: Optional[str] = None,
        remark: Optional[str] = None,
    ):
        """
        确认扣费并写积分日志。
        SQLite：只写日志，余额已在 pre_deduct 扣除。
        MySQL：写日志（余额已在 pre_deduct 落库）。
        """

    @abstractmethod
    def add_points(
        self,
        db: Session,
        user_id: int,
        amount: int,
        log_type: int,
        related_key_id: Optional[int] = None,
        model: Optional[str] = None,
        remark: Optional[str] = None,
    ):
        """增加积分并写积分日志。"""

    @abstractmethod
    def get_point_logs(
        self, db: Session, user_id: int, limit: int = 100, offset: int = 0
    ) -> list:
        """获取积分明细列表。"""

    def flush_to_db(self):
        """
        将待落库记录写入数据库（供 background_tasks 调用）。
        MySQL 后端为空操作（直接写 DB，无需 flush）。
        """


# ─────────────────────────────────────────────
# SQLite 后端实现
# ─────────────────────────────────────────────

class _SQLiteBackend(PointsBackend):
    """
    内存缓存 + 异步 flush 后端。
    适合 SQLite 单机场景，避免高频写入导致文件锁竞争。
    """

    def __init__(self):
        # { user_id: balance }
        self._balances: Dict[int, int] = {}
        # { user_id: RLock }
        self._user_locks: Dict[int, threading.RLock] = {}
        self._user_locks_meta = threading.Lock()
        # 待落库队列
        self._pending_logs: List[PendingLog] = []
        self._flush_lock = threading.Lock()

    # ── 内部辅助 ──────────────────────────────

    def _get_user_lock(self, user_id: int) -> threading.RLock:
        if user_id not in self._user_locks:
            with self._user_locks_meta:
                if user_id not in self._user_locks:
                    self._user_locks[user_id] = threading.RLock()
        return self._user_locks[user_id]

    def _load_balance_from_db(self, user_id: int) -> int:
        import app.db.database as _db_module
        db = _db_module.SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            return user.balance if user else 0
        finally:
            db.close()

    def _ensure_loaded(self, user_id: int):
        if user_id not in self._balances:
            with self._get_user_lock(user_id):
                if user_id not in self._balances:
                    self._balances[user_id] = self._load_balance_from_db(user_id)

    def _enqueue(self, entry: PendingLog):
        with self._flush_lock:
            self._pending_logs.append(entry)

    # ── 接口实现 ──────────────────────────────

    def get_balance(self, db: Session, user_id: int) -> int:
        self._ensure_loaded(user_id)
        return self._balances.get(user_id, 0)

    def pre_deduct(self, db: Session, user_id: int, amount: int) -> bool:
        self._ensure_loaded(user_id)
        with self._get_user_lock(user_id):
            current = self._balances.get(user_id, 0)
            if current < amount:
                return False
            self._balances[user_id] = current - amount
            return True

    def rollback(self, db: Session, user_id: int, amount: int):
        self._ensure_loaded(user_id)
        with self._get_user_lock(user_id):
            self._balances[user_id] = self._balances.get(user_id, 0) + amount

    def confirm_deduct(self, db, user_id, amount, log_type,
                       related_key_id=None, model=None, remark=None):
        self._ensure_loaded(user_id)
        with self._get_user_lock(user_id):
            balance_after = self._balances.get(user_id, 0)
        self._enqueue(PendingLog(
            user_id=user_id, delta=-amount, balance_after=balance_after,
            log_amount=-amount, log_type=log_type,
            related_key_id=related_key_id, model=model, remark=remark,
            created_at=int(time.time()),
        ))

    def add_points(self, db, user_id, amount, log_type,
                   related_key_id=None, model=None, remark=None):
        self._ensure_loaded(user_id)
        with self._get_user_lock(user_id):
            new_balance = self._balances.get(user_id, 0) + amount
            self._balances[user_id] = new_balance
        self._enqueue(PendingLog(
            user_id=user_id, delta=amount, balance_after=new_balance,
            log_amount=amount, log_type=log_type,
            related_key_id=related_key_id, model=model, remark=remark,
            created_at=int(time.time()),
        ))

    def get_point_logs(self, db: Session, user_id: int,
                       limit: int = 100, offset: int = 0) -> list:
        return (
            db.query(PointLog)
            .filter(PointLog.user_id == user_id)
            .order_by(PointLog.created_at.desc())
            .limit(limit).offset(offset).all()
        )

    def invalidate_cache(self, user_id: int):
        """使指定用户的内存余额失效（管理员直接改 DB 后调用）。"""
        with self._get_user_lock(user_id):
            self._balances.pop(user_id, None)

    def flush_to_db(self):
        """
        批量将 _pending_logs 落库。
        策略：drain 队列 → 聚合余额 → UPDATE users + bulk INSERT point_logs。
        失败时将本批记录塞回队列头部，等下次重试。
        """
        with self._flush_lock:
            if not self._pending_logs:
                return
            batch = self._pending_logs[:]
            self._pending_logs = []

        latest_balance: Dict[int, int] = {}
        for entry in batch:
            latest_balance[entry.user_id] = entry.balance_after

        import app.db.database as _db_module
        db = _db_module.SessionLocal()
        try:
            for user_id, balance in latest_balance.items():
                db.query(User).filter(User.id == user_id).update(
                    {"balance": balance}, synchronize_session=False
                )
            db.bulk_insert_mappings(PointLog, [
                {
                    "user_id": e.user_id, "amount": e.log_amount,
                    "type": e.log_type, "related_key_id": e.related_key_id,
                    "model": e.model, "remark": e.remark,
                    "created_at": e.created_at,
                }
                for e in batch
            ])
            db.commit()
            logger.debug(
                "[SQLiteBackend] flush 成功：%d 条日志，用户 %s",
                len(batch), list(latest_balance.keys())
            )
        except Exception as e:
            logger.error("[SQLiteBackend] flush 失败，回退队列: %s", e)
            db.rollback()
            with self._flush_lock:
                self._pending_logs = batch + self._pending_logs
        finally:
            db.close()


# ─────────────────────────────────────────────
# MySQL 后端实现
# ─────────────────────────────────────────────

class _MySQLBackend(PointsBackend):
    """
    直接写 DB 后端。
    利用 MySQL InnoDB 行锁保证并发安全，无内存状态。
    AI 响应本身耗时数秒，DB 写入毫秒级，无需缓存层。
    """

    def get_balance(self, db: Session, user_id: int) -> int:
        user = db.query(User).filter(User.id == user_id).first()
        return user.balance if user else 0

    def pre_deduct(self, db: Session, user_id: int, amount: int) -> bool:
        """
        原子扣减：UPDATE ... WHERE balance >= amount。
        affected_rows = 0 即余额不足，不需要额外加锁。
        """
        result = db.execute(
            text(
                "UPDATE users SET balance = balance - :amount "
                "WHERE id = :uid AND balance >= :amount"
            ),
            {"amount": amount, "uid": user_id},
        )
        db.commit()
        return result.rowcount == 1

    def rollback(self, db: Session, user_id: int, amount: int):
        """退还预扣的积分。"""
        db.execute(
            text("UPDATE users SET balance = balance + :amount WHERE id = :uid"),
            {"amount": amount, "uid": user_id},
        )
        db.commit()

    def confirm_deduct(self, db, user_id, amount, log_type,
                       related_key_id=None, model=None, remark=None):
        """余额已在 pre_deduct 落库，这里只写积分日志。"""
        log = PointLog(
            user_id=user_id, amount=-amount, type=log_type,
            related_key_id=related_key_id, model=model, remark=remark,
            created_at=int(time.time()),
        )
        db.add(log)
        db.commit()

    def add_points(self, db, user_id, amount, log_type,
                   related_key_id=None, model=None, remark=None):
        db.execute(
            text("UPDATE users SET balance = balance + :amount WHERE id = :uid"),
            {"amount": amount, "uid": user_id},
        )
        log = PointLog(
            user_id=user_id, amount=amount, type=log_type,
            related_key_id=related_key_id, model=model, remark=remark,
            created_at=int(time.time()),
        )
        db.add(log)
        db.commit()

    def get_point_logs(self, db: Session, user_id: int,
                       limit: int = 100, offset: int = 0) -> list:
        return (
            db.query(PointLog)
            .filter(PointLog.user_id == user_id)
            .order_by(PointLog.created_at.desc())
            .limit(limit).offset(offset).all()
        )

    def flush_to_db(self):
        """MySQL 直写模式，无待落库队列，空操作。"""


# ─────────────────────────────────────────────
# 后端工厂：根据 driver 实例化（模块级单例）
# ─────────────────────────────────────────────

def _create_backend() -> PointsBackend:
    driver = settings.database.get("driver", "sqlite")
    if driver == "mysql":
        logger.info("[PointsService] 使用 MySQLBackend（直写模式）")
        return _MySQLBackend()
    else:
        logger.info("[PointsService] 使用 SQLiteBackend（内存缓存 + flush 模式）")
        return _SQLiteBackend()


_backend: PointsBackend = _create_backend()


# ─────────────────────────────────────────────
# 对外公开接口（调用方零感知 driver）
# ─────────────────────────────────────────────

class PointsService:

    @staticmethod
    def get_user_balance(db: Session, user_id: int) -> int:
        return _backend.get_balance(db, user_id)

    @staticmethod
    def pre_deduct_points(db: Session, user_id: int, amount: int) -> bool:
        return _backend.pre_deduct(db, user_id, amount)

    @staticmethod
    def rollback_points(db: Session, user_id: int, amount: int):
        return _backend.rollback(db, user_id, amount)

    @staticmethod
    def confirm_deduct(
        db: Session,
        user_id: int,
        amount: int,
        log_type: int,
        related_key_id: Optional[int] = None,
        model: Optional[str] = None,
        remark: Optional[str] = None,
    ):
        return _backend.confirm_deduct(
            db, user_id, amount, log_type, related_key_id, model, remark
        )

    @staticmethod
    def add_points(
        db: Session,
        user_id: int,
        amount: int,
        log_type: int,
        related_key_id: Optional[int] = None,
        model: Optional[str] = None,
        remark: Optional[str] = None,
    ):
        return _backend.add_points(
            db, user_id, amount, log_type, related_key_id, model, remark
        )

    @staticmethod
    def get_point_logs(db: Session, user_id: int,
                       limit: int = 100, offset: int = 0) -> list:
        return _backend.get_point_logs(db, user_id, limit, offset)

    @staticmethod
    def invalidate_cache(user_id: int):
        """仅 SQLiteBackend 有效，MySQLBackend 为空操作。"""
        if isinstance(_backend, _SQLiteBackend):
            _backend.invalidate_cache(user_id)


# ─────────────────────────────────────────────
# flush_to_db：供 background_tasks 调用
# MySQL 模式下为空操作，SQLite 模式下批量落库
# ─────────────────────────────────────────────

def flush_to_db():
    _backend.flush_to_db()
