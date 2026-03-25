import time
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.db.database import Base

class ApiKey(Base):
    __tablename__ = "api_keys"

    id            = Column(Integer,     primary_key=True, index=True, autoincrement=True)
    user_id       = Column(Integer,     ForeignKey("users.id"), nullable=False)
    key_type      = Column(Integer,     nullable=False)           # 1=平台调用密钥, 2=厂商密钥
    provider      = Column(String(64),  nullable=True)            # 厂商标识
    encrypted_key = Column(String(512), nullable=False)           # 加密存储的密钥
    name          = Column(String(128), nullable=False)           # 密钥名称
    status        = Column(Integer,     default=0, nullable=False) # 0=正常,1=删除,2=禁用,3=超限冷却,4=无效
    cooldown_until= Column(DateTime,    nullable=True)            # 冷却截止时间（status=3时使用）
    used_count    = Column(Integer,     default=0, nullable=False)
    last_used_at  = Column(Integer,     nullable=True)
    created_at    = Column(Integer,     default=lambda: int(time.time()), nullable=False)
