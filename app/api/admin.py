from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from app.db.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.schemas.point import PointAdjustRequest
from app.schemas.key import ApiKeyResponse
from app.services.admin_service import AdminService
from app.config.settings import settings

router = APIRouter()
security = HTTPBearer()

def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取当前管理员"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.security.get('jwt_secret', 'your-jwt-secret'), algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无管理员权限",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True

@router.get("/users", response_model=List[UserResponse])
def get_users(current_admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    """管理用户列表"""
    users = AdminService.get_all_users(db)
    return users

@router.post("/users", response_model=UserResponse)
def create_user(request: UserCreate, current_admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    """创建用户"""
    try:
        user = AdminService.create_user(db, request.username, request.email, request.password)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/users/{user_id}")
def update_user_status(user_id: int, status: int, current_admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    """更新用户状态"""
    AdminService.update_user_status(db, user_id, status)
    return {"message": "用户状态已更新"}

@router.delete("/users/{user_id}")
def delete_user(user_id: int, current_admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    """删除用户"""
    AdminService.update_user_status(db, user_id, 0)  # 0 - 禁用
    return {"message": "用户已删除"}

@router.post("/points")
def adjust_user_points(request: PointAdjustRequest, current_admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    """调整用户积分"""
    AdminService.adjust_user_points(db, request.user_id, request.amount, request.remark or "管理员调整")
    return {"message": "积分已调整"}

@router.get("/keys", response_model=List[ApiKeyResponse])
def get_all_keys(current_admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    """查看所有密钥"""
    keys = AdminService.get_all_api_keys(db)
    return keys

@router.put("/keys/{key_id}")
def update_key_status(key_id: int, status: int, current_admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    """管理密钥状态"""
    AdminService.update_api_key_status(db, key_id, status)
    return {"message": "密钥状态已更新"}

@router.delete("/keys/{key_id}")
def delete_key(key_id: int, current_admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    """删除密钥"""
    AdminService.update_api_key_status(db, key_id, 1)  # 1 - 删除
    return {"message": "密钥已删除"}

@router.get("/logs")
def get_call_logs(limit: int = 100, offset: int = 0, current_admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    """查看调用日志"""
    logs = AdminService.get_call_logs(db, limit, offset)
    return logs