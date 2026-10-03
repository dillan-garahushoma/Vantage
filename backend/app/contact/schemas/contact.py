from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ContactRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str | None = None
    subject: str | None = Field(default=None, max_length=150)
    message: str = Field(..., min_length=10, max_length=5000)


class ContactResponse(BaseModel):
    message_id: int = Field(..., serialization_alias="id")
    name: str
    email: str
    subject: str | None
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
