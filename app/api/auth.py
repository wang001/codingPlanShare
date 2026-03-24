from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.admin import AdminLoginRequest, AdminLoginResponse
from app.services.auth_service import AuthService
from app.services.admin_service import AdminService

router = APIRouter()


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="用户登录",
    description=(
        "使用邮箱和密码登录，返回 JWT Token。\n\n"
        "**后续请求**：将 `access_token` 放入 `Authorization: Bearer <token>` Header。\n\n"
        "**注意**：被管理员禁用（status=0）的用户无法登录。"
    ),
)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = AuthService.authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = AuthService.create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=30),
    )
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
    )


@router.post(
    "/admin/login",
    response_model=AdminLoginResponse,
    summary="管理员登录",
    description=(
        "使用管理员密码登录（见 `config.yaml` 中 `admin.password`），返回管理员 JWT Token。\n\n"
        "**后续管理接口**：将 `access_token` 放入 `Authorization: Bearer <token>` Header。\n\n"
        "管理员 Token 与用户 Token 完全隔离，互不通用。"
    ),
)
def admin_login(request: AdminLoginRequest):
    if not AdminService.verify_admin_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = AuthService.create_access_token(
        data={"sub": "admin"},
        expires_delta=timedelta(minutes=30),
    )
    return AdminLoginResponse(access_token=access_token, token_type="bearer")
