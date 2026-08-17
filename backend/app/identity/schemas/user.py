"""
User schemas — request/response shapes for user profile endpoints.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.common.enums import UserRole


class UserResponse(BaseModel):
    """Safe representation of a User — never includes hashed_password."""

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    """Payload for PATCH /users/me."""

    full_name: str | None = None
