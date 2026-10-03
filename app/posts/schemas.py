from datetime import datetime

from pydantic import BaseModel


class PostCreate(BaseModel):
    title: str
    content: str

class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    image_url: str | None
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class PostUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
