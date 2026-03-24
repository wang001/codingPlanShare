from sqlalchemy import Column, String
from app.db.database import Base

class SystemConfig(Base):
    __tablename__ = "system_config"

    key   = Column(String(128), primary_key=True, index=True, nullable=False)
    value = Column(String(2048), nullable=False)
