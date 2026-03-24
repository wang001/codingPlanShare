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
    created_at      = Column(Integer,      default=lambda: int(time.time()), nullable=False, index=True)
