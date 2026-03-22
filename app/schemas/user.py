from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    password: str | None = None
    status: int | None = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    balance: int
    status: int
    created_at: int

    class Config:
        from_attributes = True