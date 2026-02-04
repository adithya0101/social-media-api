from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = None
