import pytest
from sqlalchemy.orm import Session
from app.db.database import get_db, Base, engine
from app.models.user import User
from app.services.key_service import KeyService

# 创建测试数据库
@pytest.fixture(scope="function")
def db():
    # 创建表
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    yield db
    # 清理表
    Base.metadata.drop_all(bind=engine)
    db.close()

# 测试生成API密钥
def test_generate_api_key():
    key = KeyService.generate_api_key()
    assert key is not None
    assert isinstance(key, str)
    assert len(key) > 0

# 测试创建API密钥
def test_create_api_key(db: Session):
    # 创建测试用户
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="hashedpassword",
        balance=100,
        status=1
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 测试创建平台调用密钥
    platform_key = KeyService.create_api_key(
        db=db,
        user_id=user.id,
        key_type=1,
        name="测试平台密钥"
    )
    assert platform_key is not None
    assert platform_key.user_id == user.id
    assert platform_key.key_type == 1
    assert platform_key.name == "测试平台密钥"
    
    # 测试创建厂商密钥
    provider_key = KeyService.create_api_key(
        db=db,
        user_id=user.id,
        key_type=2,
        name="测试厂商密钥",
        provider="minimax",
        raw_key="test-api-key"
    )
    assert provider_key is not None
    assert provider_key.user_id == user.id
    assert provider_key.key_type == 2
    assert provider_key.provider == "minimax"
    assert provider_key.name == "测试厂商密钥"

# 测试获取用户密钥
def test_get_user_keys(db: Session):
    # 创建测试用户
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="hashedpassword",
        balance=100,
        status=1
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 创建测试密钥
    KeyService.create_api_key(
        db=db,
        user_id=user.id,
        key_type=1,
        name="测试平台密钥"
    )
    KeyService.create_api_key(
        db=db,
        user_id=user.id,
        key_type=2,
        name="测试厂商密钥",
        provider="minimax",
        raw_key="test-api-key"
    )
    
    # 测试获取所有密钥
    keys = KeyService.get_user_keys(db, user.id)
    assert len(keys) == 2
    
    # 测试获取平台密钥
    platform_keys = KeyService.get_user_keys(db, user.id, key_type=1)
    assert len(platform_keys) == 1
    assert platform_keys[0].key_type == 1
    
    # 测试获取厂商密钥
    provider_keys = KeyService.get_user_keys(db, user.id, key_type=2)
    assert len(provider_keys) == 1
    assert provider_keys[0].key_type == 2

# 测试更新密钥状态
def test_update_key_status(db: Session):
    # 创建测试用户
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="hashedpassword",
        balance=100,
        status=1
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 创建测试密钥
    key = KeyService.create_api_key(
        db=db,
        user_id=user.id,
        key_type=1,
        name="测试平台密钥"
    )
    assert key.status == 0
    
    # 测试更新状态
    KeyService.update_key_status(db, key.id, 2)  # 2 - 禁用
    updated_key = KeyService.get_key_by_id(db, key.id)
    assert updated_key.status == 2