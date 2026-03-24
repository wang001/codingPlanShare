import time
from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.database import Base

class PointLog(Base):
    __tablename__ = "point_logs"

    id             = Column(Integer,     primary_key=True, index=True, autoincrement=True)
    user_id        = Column(Integer,     ForeignKey("users.id"), nullable=False, index=True)
    amount         = Column(Integer,     nullable=False)           # 变动量（负=扣, 正=增）
    type           = Column(Integer,     nullable=False)           # 1=调用消耗, 2=托管收益, 3=管理员调整
    related_key_id = Column(Integer,     ForeignKey("api_keys.id"), nullable=True)
    model          = Column(String(128), nullable=True)
    remark         = Column(String(256), nullable=True)
    created_at     = Column(Integer,     default=lambda: int(time.time()), nullable=False, index=True)
