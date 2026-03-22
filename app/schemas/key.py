from pydantic import BaseModel

class ApiKeyCreate(BaseModel):
    name: str
    key_type: int  # 1 - 平台调用密钥，2 - 用户托管的厂商密钥
    provider: str | None = None  # 厂商类型（仅厂商密钥有效）
    encrypted_key: str | None = None  # 加密后的密钥内容（仅厂商密钥需要）

class ApiKeyUpdate(BaseModel):
    name: str | None = None
    status: int | None = None

class ApiKeyResponse(BaseModel):
    id: int
    user_id: int
    key_type: int
    provider: str | None
    name: str
    status: int
    used_count: int
    last_used_at: int | None
    created_at: int
    encrypted_key: str

    class Config:
        from_attributes = True