from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    balance = Column(Integer, default=0, nullable=False)  # 积分余额，单位：分
    status = Column(Integer, default=1, nullable=False)  # 状态：0 - 禁用，1 - 正常
    created_at = Column(Integer, default=func.extract('epoch', func.now()), nullable=False)