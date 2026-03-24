import time
from sqlalchemy import Column, Integer, String
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username      = Column(String(64),  unique=True, index=True, nullable=False)
    email         = Column(String(128), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    balance       = Column(Integer, default=0,  nullable=False)
    status        = Column(Integer, default=1,  nullable=False)  # 1=正常, 0=禁用
    created_at    = Column(Integer, default=lambda: int(time.time()), nullable=False)
