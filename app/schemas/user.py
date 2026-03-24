from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(..., description="用户名，全局唯一", example="alice")
    email: str = Field(..., description="邮箱，全局唯一，用于登录", example="alice@example.com")
    password: str = Field(..., description="初始密码", example="changeme123")


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, description="新用户名")
    email: str | None = Field(default=None, description="新邮箱")
    password: str | None = Field(default=None, description="新密码")
    status: int | None = Field(default=None, description="用户状态：0=已禁用，1=正常")


class UserResponse(BaseModel):
    id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    balance: int = Field(..., description="积分余额（单位：分）。注意：该值为内存中的实时值，每秒异步落库，服务刚启动时从数据库加载")
    status: int = Field(..., description="用户状态：0=已禁用（无法登录，名下所有密钥 API 调用返回 401），1=正常")
    created_at: int = Field(..., description="注册时间戳（Unix 秒）")

    class Config:
        from_attributes = True
