from pydantic import BaseModel, Field
from typing import Literal


class ApiKeyCreate(BaseModel):
    name: str = Field(..., description="密钥名称，用户自定义", example="我的 ModelScope 密钥")
    key_type: int = Field(
        ...,
        description="密钥类型：1=平台调用密钥（系统自动生成 key 值，用于调用本平台对话接口）；2=厂商托管密钥（用户提供自己的厂商 API Key，服务端加密存储）",
        example=2,
    )
    provider: str | None = Field(
        default=None,
        description=(
            "厂商标识，key_type=2 时必填，须在系统白名单内（防止 SSRF）。\n"
            "按量付费通道：modelscope / zhipu / minimax / alibaba / tencent / baidu / kimi / deepseek / siliconflow\n"
            "Coding Plan 专属通道：alibaba_coding（阿里云百炼，key 格式 sk-sp-xxxxx）/ "
            "zhipu_coding（智谱 GLM Coding Plan）/ minimax_coding（MiniMax Coding Plan）\n"
            "注意：Coding Plan 通道与按量通道 key 不互通，请勿混用。\n"
            "仅测试：mock"
        ),
        example="alibaba_coding",
    )
    encrypted_key: str | None = Field(
        default=None,
        description=(
            "厂商原始 API Key，key_type=2 时必填，服务端使用 Fernet 对称加密后存储，明文不落库。"
            "mock provider 支持特殊格式：mock（正常）/ mock:slow（慢响应）/ mock:fail（总失败）/ mock:fail_rate=0.3（30% 失败）"
        ),
        example="ms-xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )


class ApiKeyUpdate(BaseModel):
    name: str | None = Field(default=None, description="新密钥名称")
    status: int | None = Field(
        default=None,
        description="新状态：0=正常，1=已删除（软删除），2=已禁用，3=超限，4=无效",
    )


class ApiKeyResponse(BaseModel):
    id: int = Field(..., description="密钥 ID")
    user_id: int = Field(..., description="所属用户 ID")
    key_type: int = Field(..., description="密钥类型：1=平台调用密钥，2=厂商托管密钥")
    provider: str | None = Field(
        ...,
        description=(
            "厂商标识（仅厂商密钥有值）。"
            "按量：modelscope / zhipu / minimax / alibaba / tencent / baidu / kimi / deepseek / siliconflow；"
            "Coding Plan：alibaba_coding / zhipu_coding / minimax_coding；"
            "测试：mock"
        )
    )
    name: str = Field(..., description="密钥名称")
    status: int = Field(
        ...,
        description=(
            "密钥状态："
            "0=正常（可被路由选中）；"
            "1=已删除（软删除，不可恢复）；"
            "2=已禁用（管理员手动禁用，可恢复）；"
            "3=超限（厂商返回额度超限时自动标记，冷却后可恢复）；"
            "4=无效（厂商认证失败时自动标记，需用户更换 key）"
        ),
    )
    used_count: int = Field(..., description="累计被调用次数")
    last_used_at: int | None = Field(..., description="最后使用时间戳（Unix 秒），从未使用则为 null")
    created_at: int = Field(..., description="创建时间戳（Unix 秒）")
    encrypted_key: str = Field(
        ...,
        description="平台密钥（key_type=1）：明文 key 值，用于调用对话接口的 api-key Header；厂商密钥（key_type=2）：Fernet 加密后的密文，不可直接使用",
    )

    class Config:
        from_attributes = True
