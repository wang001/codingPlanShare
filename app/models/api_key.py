from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base

class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key_type = Column(Integer, nullable=False)  # 1 - 平台调用密钥，2 - 用户托管的厂商密钥
    provider = Column(String, nullable=True)  # 厂商类型（仅厂商密钥有效）
    encrypted_key = Column(String, nullable=False)  # 加密后的密钥内容
    name = Column(String, nullable=False)  # 密钥名称
    status = Column(Integer, default=0, nullable=False)  # 状态：0 - 正常，1 - 删除，2 - 禁用，3 - 超限，4 - 无效
    used_count = Column(Integer, default=0, nullable=False)  # 累计调用次数
    last_used_at = Column(Integer, nullable=True)  # 最后使用时间戳
    created_at = Column(Integer, default=func.extract('epoch', func.now()), nullable=False)