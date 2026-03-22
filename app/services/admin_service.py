from typing import List
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.api_key import ApiKey
from app.models.call_log import CallLog
from app.services.auth_service import AuthService
from app.services.points_service import PointsService
from app.config.settings import settings

class AdminService:
    @staticmethod
    def verify_admin_password(password: str) -> bool:
        """验证管理员密码"""
        return password == settings.admin.get('password', 'admin123')

    @staticmethod
    def get_all_users(db: Session) -> List[User]:
        """获取所有用户"""
        return db.query(User).all()

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        """通过ID获取用户"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def create_user(db: Session, username: str, email: str, password: str) -> User:
        """创建用户"""
        # 检查用户名和邮箱是否已存在
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user:
            raise ValueError("用户名或邮箱已存在")
        
        # 创建新用户
        hashed_password = AuthService.get_password_hash(password)
        user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            balance=0,
            status=1
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_user_status(db: Session, user_id: int, status: int):
        """更新用户状态"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.status = status
            db.commit()

    @staticmethod
    def adjust_user_points(db: Session, user_id: int, amount: int, remark: str):
        """调整用户积分"""
        PointsService.add_points(db, user_id, amount, 3, remark=remark)

    @staticmethod
    def get_all_api_keys(db: Session) -> List[ApiKey]:
        """获取所有API密钥"""
        return db.query(ApiKey).filter(ApiKey.status != 1).all()

    @staticmethod
    def get_api_key_by_id(db: Session, key_id: int) -> ApiKey:
        """通过ID获取API密钥"""
        return db.query(ApiKey).filter(ApiKey.id == key_id).first()

    @staticmethod
    def update_api_key_status(db: Session, key_id: int, status: int):
        """更新API密钥状态"""
        key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
        if key:
            key.status = status
            db.commit()

    @staticmethod
    def get_call_logs(db: Session, limit: int = 100, offset: int = 0) -> List[CallLog]:
        """获取调用日志"""
        return db.query(CallLog).order_by(CallLog.created_at.desc()).limit(limit).offset(offset).all()