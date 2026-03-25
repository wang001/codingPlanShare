"""
pytest 公共 fixture 配置。

使用内存 SQLite 数据库隔离测试，避免多个测试共用 data/app.db 导致的 UNIQUE 冲突。
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base


@pytest.fixture(scope="function")
def db():
    """
    每个测试函数使用独立的内存 SQLite 数据库。
    测试结束后自动清理表结构和内存积分缓存。
    """
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()

    # 替换 app.db.database 中的 engine/SessionLocal，让 service 层也用测试 DB
    import app.db.database as db_module
    original_engine = db_module.engine
    original_session_local = db_module.SessionLocal

    db_module.engine = test_engine
    db_module.SessionLocal = TestingSessionLocal

    yield session

    # 清理内存积分缓存（仅 SQLiteBackend 有效）
    from app.services.points_service import _backend, _SQLiteBackend
    if isinstance(_backend, _SQLiteBackend):
        _backend._balances.clear()

    session.close()
    Base.metadata.drop_all(bind=test_engine)

    db_module.engine = original_engine
    db_module.SessionLocal = original_session_local
