import pytest
from sqlalchemy.orm import Session
from app.db.database import get_db, Base, engine
from app.models.user import User
from app.services.points_service import PointsService

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

# 测试获取用户余额
def test_get_user_balance(db: Session):
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
    
    # 测试获取余额
    balance = PointsService.get_user_balance(db, user.id)
    assert balance == 100

# 测试预扣积分
def test_pre_deduct_points(db: Session):
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
    
    # 测试预扣成功
    result = PointsService.pre_deduct_points(db, user.id, 50)
    assert result is True
    assert user.balance == 50
    
    # 测试预扣失败（余额不足）
    result = PointsService.pre_deduct_points(db, user.id, 100)
    assert result is False
    assert user.balance == 50

# 测试回滚积分
def test_rollback_points(db: Session):
    # 创建测试用户
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="hashedpassword",
        balance=50,
        status=1
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 测试回滚积分
    PointsService.rollback_points(db, user.id, 50)
    assert user.balance == 100

# 测试增加积分
def test_add_points(db: Session):
    # 创建测试用户
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="hashedpassword",
        balance=50,
        status=1
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 测试增加积分
    PointsService.add_points(db, user.id, 50, 2, remark="测试增加积分")
    assert user.balance == 100