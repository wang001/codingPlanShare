import pytest
from sqlalchemy.orm import Session
from app.models.user import User
from app.services.points_service import PointsService, _balances


# 测试获取用户余额
def test_get_user_balance(db: Session):
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

    balance = PointsService.get_user_balance(db, user.id)
    assert balance == 100


# 测试预扣积分
def test_pre_deduct_points(db: Session):
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

    # 预扣成功：内存余额从 100 变为 50
    result = PointsService.pre_deduct_points(db, user.id, 50)
    assert result is True
    assert PointsService.get_user_balance(db, user.id) == 50

    # 余额不足：内存余额保持 50
    result = PointsService.pre_deduct_points(db, user.id, 100)
    assert result is False
    assert PointsService.get_user_balance(db, user.id) == 50


# 测试回滚积分
def test_rollback_points(db: Session):
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

    PointsService.rollback_points(db, user.id, 50)
    assert PointsService.get_user_balance(db, user.id) == 100


# 测试增加积分
def test_add_points(db: Session):
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

    PointsService.add_points(db, user.id, 50, 2, remark="测试增加积分")
    assert PointsService.get_user_balance(db, user.id) == 100
