"""
Auth schemas — request/response shapes for authentication endpoints.
"""
from pydantic import BaseModel, EmailStr, field_validator

from app.common.validators import validate_password_strength


class LoginRequest(BaseModel):
    """Payload for POST /auth/login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Returned on successful login or token refresh."""

    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    """Payload for POST /auth/register."""

    email: EmailStr
    password: str
    full_name: str

    @field_validator("password")
    @classmethod
    def _validate_password(cls, v: str) -> str:
        return validate_password_strength(v)
