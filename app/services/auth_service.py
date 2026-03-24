from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.api_key import ApiKey
from app.config.settings import settings

# 使用 pbkdf2_sha256 作为密码哈希方案，避免 bcrypt 的密码长度限制
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """获取密码哈希"""
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.security.get('jwt_secret', 'your-jwt-secret'), algorithm="HS256")
        return encoded_jwt

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """通过邮箱获取用户"""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """通过ID获取用户"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def verify_api_key(db: Session, api_key: str) -> Optional[ApiKey]:
        """验证API密钥：密钥状态正常 且 所属用户未被禁用"""
        key = db.query(ApiKey).filter(
            ApiKey.encrypted_key == api_key,
            ApiKey.status == 0,
        ).first()
        if key is None:
            return None
        # 联查用户状态，禁用用户的密钥一并视为无效
        user = db.query(User).filter(User.id == key.user_id, User.status == 1).first()
        if user is None:
            return None
        return key

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """认证用户"""
        user = AuthService.get_user_by_email(db, email)
        if not user:
            return None
        if not AuthService.verify_password(password, user.password_hash):
            return None
        if user.status != 1:
            return None
        return user