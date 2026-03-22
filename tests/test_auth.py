import pytest
from sqlalchemy.orm import Session
from app.db.database import get_db, Base, engine
from app.models.user import User
from app.services.auth_service import AuthService

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

# 测试用户认证
def test_authenticate_user(db: Session):
    # 创建测试用户
    hashed_password = AuthService.get_password_hash("test123")
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=hashed_password,
        balance=100,
        status=1
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 测试正确的密码
    authenticated_user = AuthService.authenticate_user(db, "test@example.com", "test123")
    assert authenticated_user is not None
    assert authenticated_user.username == "testuser"
    
    # 测试错误的密码
    authenticated_user = AuthService.authenticate_user(db, "test@example.com", "wrongpassword")
    assert authenticated_user is None
    
    # 测试不存在的用户
    authenticated_user = AuthService.authenticate_user(db, "nonexistent@example.com", "test123")
    assert authenticated_user is None

# 测试密码哈希
def test_password_hash():
    password = "test123"
    hashed = AuthService.get_password_hash(password)
    assert AuthService.verify_password(password, hashed)
    assert not AuthService.verify_password("wrongpassword", hashed)

# 测试JWT令牌
def test_create_access_token():
    data = {"sub": "1"}
    token = AuthService.create_access_token(data)
    assert token is not None
    assert isinstance(token, str)