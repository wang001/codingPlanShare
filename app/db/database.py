import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config.settings import settings

db_config = settings.database
driver = db_config['driver']

if driver == 'sqlite':
    DATABASE_URL = f"sqlite:///{db_config['path']}"
    engine_kwargs = {
        "connect_args": {"check_same_thread": False},
    }
elif driver == 'mysql':
    host     = db_config['host']
    port     = db_config.get('port', 3306)
    user     = db_config['user']
    password = db_config['password']
    name     = db_config['name']
    DATABASE_URL = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"
    engine_kwargs = {
        "pool_size":     db_config.get('pool_size', 10),
        "max_overflow":  db_config.get('max_overflow', 20),
        "pool_recycle":  db_config.get('pool_recycle', 1800),
        "pool_pre_ping": True,
    }
else:
    raise ValueError(f"Unsupported database driver: {driver}")

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
