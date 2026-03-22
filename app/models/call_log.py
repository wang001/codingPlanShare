from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base

class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True)  # 本次使用的厂商密钥 ID
    model = Column(String, nullable=False)  # 模型名称
    status = Column(Integer, nullable=False)  # 调用状态：0 - 失败，1 - 成功
    error_msg = Column(String, nullable=True)  # 错误信息（失败时）
    ip = Column(String, nullable=True)  # 调用者 IP
    created_at = Column(Integer, default=func.extract('epoch', func.now()), nullable=False)