"""Identity Pydantic schemas — request and response models."""
from pydantic import BaseModel, EmailStr, Field

from app.common.enums import UserRole


# --- Auth schemas ---

class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.resident
    phoneno: str | None = None
    unit_no: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- User schemas ---

class UserResponse(BaseModel):
    user_id: int
    email: str
    full_name: str
    role: str
    unit_no: str | None
    email_verified: bool
    hoa_approved: bool

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
