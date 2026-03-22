from pydantic import BaseModel

class PointLogResponse(BaseModel):
    id: int
    user_id: int
    amount: int
    type: int
    related_key_id: int | None
    model: str | None
    remark: str | None
    created_at: int

    class Config:
        from_attributes = True

class PointAdjustRequest(BaseModel):
    user_id: int
    amount: int
    remark: str | None = None