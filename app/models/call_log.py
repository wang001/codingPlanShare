import time
from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.database import Base

class CallLog(Base):
    __tablename__ = "call_logs"

    id              = Column(Integer,      primary_key=True, index=True, autoincrement=True)
    user_id         = Column(Integer,      ForeignKey("users.id"), nullable=False, index=True)
    provider_key_id = Column(Integer,      ForeignKey("api_keys.id"), nullable=True)
    model           = Column(String(128),  nullable=False)
    status          = Column(Integer,      nullable=False)  # 0=失败, 1=成功
    error_msg       = Column(String(1024), nullable=True)
    ip              = Column(String(64),   nullable=True)
    # token 用量（成功时填入，失败时为 None）
    prompt_tokens      = Column(Integer, nullable=True)
    completion_tokens  = Column(Integer, nullable=True)
    total_tokens       = Column(Integer, nullable=True)
    # 本次实际扣除积分数（差异计费后的真实值，便于对账）
    points_deducted    = Column(Integer, nullable=True)
    created_at      = Column(Integer,      default=lambda: int(time.time()), nullable=False, index=True)
