from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import yaml
import os

# 加载配置
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.yaml')
with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 获取数据库配置
db_config = config['database']
if db_config['driver'] == 'sqlite':
    DATABASE_URL = f"sqlite:///{db_config['path']}"
else:
    # 支持其他数据库，暂时只实现SQLite
    raise ValueError(f"Unsupported database driver: {db_config['driver']}")

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if db_config['driver'] == 'sqlite' else {}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

# 依赖项，用于获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()