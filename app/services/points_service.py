"""
积分服务 - 高并发安全设计
=========================

架构说明：
  - 内存余额（_balances）是唯一的实时计算来源，启动时从数据库加载
  - per-user 锁（_user_locks）保证同一用户的读-改-写是原子的，不同用户完全并行
  - 每次扣/增积分产生一条 PendingLog，积攒在 _pending_logs 队列
  - 后台任务每秒调用 flush_to_db()，批量写入数据库（余额 + 日志）
  - 优雅停机时 flush_to_db() 会被再调用一次，确保不丢数据

并发保证：
  - pre_deduct / rollback / confirm / add_points 全部在 per-user 锁内完成
  - 持锁时间 < 1ms（纯内存操作），厂商 API 调用在锁外，不阻塞其他请求
  - flush_to_db 使用独立的全局锁 drain _pending_logs，与业务锁不嵌套，避免死锁
"""

import threading
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.point_log import PointLog
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 内部数据结构
# ─────────────────────────────────────────────

@dataclass
class PendingLog:
    """待落库的积分变动记录"""
    user_id: int
    delta: int              # 最终余额变动量（负数=扣，正数=增）
    balance_after: int      # 变动后余额（用于更新 users.balance）
    log_amount: int         # 写入 point_logs.amount 的值（可与 delta 不同，如预扣后确认）
    log_type: int
    related_key_id: Optional[int]
    model: Optional[str]
    remark: Optional[str]
    created_at: int         # 秒级时间戳，由业务层传入保证顺序


# ─────────────────────────────────────────────
# 全局状态（模块级单例）
# ─────────────────────────────────────────────

# { user_id: balance }  —— 内存中的实时余额
_balances: Dict[int, int] = {}

# { user_id: RLock }  —— per-user 业务锁
_user_locks: Dict[int, threading.RLock] = {}
_user_locks_meta = threading.Lock()   # 保护 _user_locks 字典本身的扩充

# 待落库队列，由 _flush_lock 保护
_pending_logs: List[PendingLog] = []
_flush_lock = threading.Lock()

# 标记是否已从数据库完成初始加载
_initialized = False
_init_lock = threading.Lock()


# ─────────────────────────────────────────────
# 内部辅助函数
# ─────────────────────────────────────────────

def _get_user_lock(user_id: int) -> threading.RLock:
    """获取（或创建）per-user RLock，线程安全。"""
    if user_id not in _user_locks:
        with _user_locks_meta:
            if user_id not in _user_locks:
                _user_locks[user_id] = threading.RLock()
    return _user_locks[user_id]


def _load_user_balance_from_db(user_id: int) -> int:
    """从数据库加载单个用户余额（仅在缓存缺失时调用）。
    注意：动态引用 app.db.database.SessionLocal，确保测试 monkey-patch 生效。
    """
    import app.db.database as _db_module
    db = _db_module.SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        return user.balance if user else 0
    finally:
        db.close()


def _ensure_balance_loaded(user_id: int):
    """确保内存中有该用户的余额（懒加载，仅首次）。"""
    if user_id not in _balances:
        with _get_user_lock(user_id):
            # double-check
            if user_id not in _balances:
                _balances[user_id] = _load_user_balance_from_db(user_id)


def _enqueue_log(entry: PendingLog):
    """将一条待落库记录加入队列（线程安全）。"""
    with _flush_lock:
        _pending_logs.append(entry)


# ─────────────────────────────────────────────
# 公开 API
# ─────────────────────────────────────────────

class PointsService:

    @staticmethod
    def get_user_balance(db: Session, user_id: int) -> int:
        """获取用户实时积分余额（从内存，极快）。"""
        _ensure_balance_loaded(user_id)
        return _balances.get(user_id, 0)

    @staticmethod
    def pre_deduct_points(db: Session, user_id: int, amount: int) -> bool:
        """
        预扣积分（原子操作）。
        成功返回 True，余额不足返回 False。
        持锁时间 < 1ms，不影响并发性能。
        """
        _ensure_balance_loaded(user_id)
        with _get_user_lock(user_id):
            current = _balances.get(user_id, 0)
            if current < amount:
                return False
            _balances[user_id] = current - amount
            return True

    @staticmethod
    def rollback_points(db: Session, user_id: int, amount: int):
        """
        回滚预扣的积分（原子操作）。
        调用时机：厂商 API 调用失败且无法重试时。
        注意：rollback 本身不产生 point_log，只还原内存余额。
        """
        _ensure_balance_loaded(user_id)
        with _get_user_lock(user_id):
            _balances[user_id] = _balances.get(user_id, 0) + amount

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
        """
        确认扣费：内存余额已在 pre_deduct 时扣除，这里只生成落库记录。
        日志将在下一次 flush（≤1秒后）写入数据库。
        """
        _ensure_balance_loaded(user_id)
        with _get_user_lock(user_id):
            balance_after = _balances.get(user_id, 0)

        _enqueue_log(PendingLog(
            user_id=user_id,
            delta=-amount,
            balance_after=balance_after,
            log_amount=-amount,
            log_type=log_type,
            related_key_id=related_key_id,
            model=model,
            remark=remark,
            created_at=int(time.time()),
        ))

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
        """
        增加积分（原子操作）。
        用于托管收益、管理员调整等场景。
        """
        _ensure_balance_loaded(user_id)
        with _get_user_lock(user_id):
            new_balance = _balances.get(user_id, 0) + amount
            _balances[user_id] = new_balance

        _enqueue_log(PendingLog(
            user_id=user_id,
            delta=amount,
            balance_after=new_balance,
            log_amount=amount,
            log_type=log_type,
            related_key_id=related_key_id,
            model=model,
            remark=remark,
            created_at=int(time.time()),
        ))

    @staticmethod
    def get_point_logs(db: Session, user_id: int, limit: int = 100, offset: int = 0):
        """获取积分明细（从数据库，已落库的记录）。"""
        return (
            db.query(PointLog)
            .filter(PointLog.user_id == user_id)
            .order_by(PointLog.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def invalidate_cache(user_id: int):
        """
        使指定用户的内存余额失效，下次访问时从数据库重新加载。
        用于管理员直接修改数据库余额后的同步。
        """
        with _get_user_lock(user_id):
            _balances.pop(user_id, None)


# ─────────────────────────────────────────────
# 落库函数（由后台任务和优雅停机调用）
# ─────────────────────────────────────────────

def flush_to_db():
    """
    将 _pending_logs 队列中所有待落库记录批量写入数据库。

    策略：
      1. 用 _flush_lock drain 出当前队列（不阻塞新增），释放锁后再做 DB 操作
      2. 按 user_id 聚合 delta，一次 UPDATE 更新余额（减少锁竞争）
      3. 批量 INSERT point_logs
      4. 单次事务，失败整体回滚并把记录塞回队列头部，等下次重试

    注意：
      - 此函数是线程安全的，可从后台线程或主线程（优雅停机）调用
      - 数据库余额以内存余额为准（直接写 balance_after），不做加减运算，避免双写冲突
    """
    global _pending_logs

    # Step 1：drain 队列（极短持锁）
    with _flush_lock:
        if not _pending_logs:
            return
        batch = _pending_logs[:]
        _pending_logs = []

    # Step 2：按 user_id 取最新余额（batch 按时间顺序，取最后一条的 balance_after）
    latest_balance: Dict[int, int] = {}
    for entry in batch:
        latest_balance[entry.user_id] = entry.balance_after

    import app.db.database as _db_module
    db = _db_module.SessionLocal()
    try:
        # Step 3：更新余额（覆盖写，以内存为准）
        for user_id, balance in latest_balance.items():
            db.query(User).filter(User.id == user_id).update(
                {"balance": balance},
                synchronize_session=False,
            )

        # Step 4：批量插入日志
        db.bulk_insert_mappings(PointLog, [
            {
                "user_id": e.user_id,
                "amount": e.log_amount,
                "type": e.log_type,
                "related_key_id": e.related_key_id,
                "model": e.model,
                "remark": e.remark,
                "created_at": e.created_at,
            }
            for e in batch
        ])

        db.commit()
        logger.debug(f"[flush_to_db] 落库成功：{len(batch)} 条日志，涉及用户 {list(latest_balance.keys())}")

    except Exception as e:
        logger.error(f"[flush_to_db] 落库失败，回退到队列: {e}")
        db.rollback()
        # 把这批记录塞回队列头部，等下次 flush 重试
        with _flush_lock:
            _pending_logs = batch + _pending_logs
    finally:
        db.close()
