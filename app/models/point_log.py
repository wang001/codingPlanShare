from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base

class PointLog(Base):
    __tablename__ = "point_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # 变动数量，正数为增加，负数为扣减
    type = Column(Integer, nullable=False)  # 变动类型：1 - 调用消耗，2 - 托管收益，3 - 管理员调整，4 - 平台收入
    related_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True)  # 关联的密钥 ID
    model = Column(String, nullable=True)  # 关联的模型
    remark = Column(String, nullable=True)  # 备注
    created_at = Column(Integer, default=func.extract('epoch', func.now()), nullable=False)