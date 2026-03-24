from pydantic import BaseModel, Field
from typing import Optional


class PointLogResponse(BaseModel):
    id: int = Field(..., description="记录 ID")
    user_id: int = Field(..., description="用户 ID")
    amount: int = Field(..., description="积分变动量：正数=增加，负数=扣减")
    type: int = Field(
        ...,
        description=(
            "变动类型："
            "1=调用消耗（用户使用平台密钥调用对话接口，按次扣减）；"
            "2=托管收益（用户的厂商密钥被平台调用，自动获得积分奖励）；"
            "3=管理员调整（管理员手动增减）；"
            "4=平台收入（平台抽取差价，当前版本预留未启用）"
        ),
    )
    related_key_id: int | None = Field(..., description="关联密钥 ID（触发此次变动的密钥）")
    model: str | None = Field(..., description="关联模型名称（含 provider 前缀，如 modelscope/moonshotai/Kimi-K2.5）")
    remark: str | None = Field(..., description="备注信息")
    created_at: int = Field(..., description="时间戳（Unix 秒）")

    class Config:
        from_attributes = True


class PointAdjustRequest(BaseModel):
    user_id: int = Field(..., description="目标用户 ID")
    amount: int = Field(..., description="调整量：正数=增加积分，负数=扣减积分", example=100)
    remark: str | None = Field(default=None, description="调整原因备注", example="活动赠送")
