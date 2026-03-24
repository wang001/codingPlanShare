from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(..., description="用户邮箱", example="admin@example.com")
    password: str = Field(..., description="用户密码", example="admin123")


class LoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT Token，后续请求放入 Authorization: Bearer <token> Header")
    token_type: str = Field(default="bearer", description="Token 类型，固定值 bearer")
    user_id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")


class AdminLoginRequest(BaseModel):
    password: str = Field(..., description="管理员密码（见 config.yaml 中 admin.password）", example="admin123")


class AdminLoginResponse(BaseModel):
    access_token: str = Field(..., description="管理员 JWT Token，后续管理接口放入 Authorization: Bearer <token> Header")
    token_type: str = Field(default="bearer", description="Token 类型，固定值 bearer")
