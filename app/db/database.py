from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import yaml
import os

# 加载配置
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.yaml')
with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

db_config = config['database']
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
    # pymysql + charset utf8mb4
    DATABASE_URL = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"
    engine_kwargs = {
        "pool_size":    db_config.get('pool_size', 10),
        "max_overflow": db_config.get('max_overflow', 20),
        "pool_recycle": db_config.get('pool_recycle', 1800),
        "pool_pre_ping": True,   # 自动剔除失效连接
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
