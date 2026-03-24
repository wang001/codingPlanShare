from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    password: str = Field(..., description="管理员密码（见 config.yaml 中 admin.password）", example="admin123")


class AdminLoginResponse(BaseModel):
    access_token: str = Field(..., description="管理员 JWT Token，后续管理接口放入 Authorization: Bearer <token> Header")
    token_type: str = Field(default="bearer", description="Token 类型，固定值 bearer")
