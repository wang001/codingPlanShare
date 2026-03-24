from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
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

@router.get("/users", response_model=List[UserResponse], summary="用户列表", description="返回所有用户信息，含积分余额和状态。")
def get_users(current_admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    return AdminService.get_all_users(db)


@router.post("/users", response_model=UserResponse, summary="创建用户", description="创建新用户，初始积分余额为 0，状态为正常（1）。用户名和邮箱须全局唯一。")
def create_user(request: UserCreate, current_admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    try:
        return AdminService.create_user(db, request.username, request.email, request.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/users/{user_id}",
    summary="更新用户状态",
    description="修改用户状态。**status=0（禁用）**：用户无法登录，且其名下所有平台密钥的 API 调用立即返回 401。**status=1（正常）**：恢复正常。",
)
def update_user_status(
    user_id: int,
    status: int = Query(..., description="用户状态：0=禁用，1=正常"),
    current_admin: bool = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    AdminService.update_user_status(db, user_id, status)
    return {"message": "用户状态已更新"}


@router.delete("/users/{user_id}", summary="禁用用户", description="将用户状态置为 0（禁用）。注意：这是软禁用，不是物理删除。")
def delete_user(user_id: int, current_admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    AdminService.update_user_status(db, user_id, 0)
    return {"message": "用户已禁用"}


@router.post(
    "/points",
    summary="调整用户积分",
    description="手动增减指定用户的积分余额。amount 为正数时增加，为负数时扣减。调整记录会写入 point_logs（type=3 管理员调整）。",
)
def adjust_user_points(request: PointAdjustRequest, current_admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    AdminService.adjust_user_points(db, request.user_id, request.amount, request.remark or "管理员调整")
    return {"message": "积分已调整"}


@router.get("/keys", response_model=List[ApiKeyResponse], summary="所有密钥列表", description="返回所有用户的密钥（已删除的 status=1 过滤），含加密密文。平台密钥（key_type=1）的 encrypted_key 为明文 key 值；厂商密钥（key_type=2）为 Fernet 密文。")
def get_all_keys(current_admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    return AdminService.get_all_api_keys(db)


@router.put(
    "/keys/{key_id}",
    summary="更新密钥状态",
    description=(
        "修改密钥状态：\n"
        "- `0` 正常：可被路由选中\n"
        "- `1` 已删除：软删除，不可恢复\n"
        "- `2` 已禁用：手动禁用，可恢复\n"
        "- `3` 超限：厂商额度超限，冷却后可恢复\n"
        "- `4` 无效：厂商认证失败，需用户更换"
    ),
)
def update_key_status(
    key_id: int,
    status: int = Query(..., description="密钥状态：0=正常，1=已删除，2=已禁用，3=超限，4=无效"),
    current_admin: bool = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    AdminService.update_api_key_status(db, key_id, status)
    return {"message": "密钥状态已更新"}


@router.delete("/keys/{key_id}", summary="删除密钥", description="软删除密钥，将 status 置为 1（已删除）。不可恢复。")
def delete_key(key_id: int, current_admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    AdminService.update_api_key_status(db, key_id, 1)
    return {"message": "密钥已删除"}


@router.get(
    "/logs",
    summary="调用日志",
    description=(
        "返回所有用户的 API 调用记录，按时间倒序排列。\n\n"
        "**status 字段**：0=失败，1=成功。\n"
        "失败时 `error_msg` 字段包含厂商返回的错误信息，可用于排查密钥问题。"
    ),
)
def get_call_logs(
    limit: int = Query(default=100, ge=1, le=500, description="返回条数上限，最大 500"),
    offset: int = Query(default=0, ge=0, description="分页偏移量"),
    current_admin: bool = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return AdminService.get_call_logs(db, limit, offset)