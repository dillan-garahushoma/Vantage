"""Identity Pydantic schemas — request and response models."""
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Auth schemas ---

class RegisterRequest(BaseModel):
    """Public registration contract.

    Privileged roles are deliberately absent: HOA and provider access is
    provisioned through an existing estate membership, never self-selected.
    """

    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    phoneno: str | None = None
    unit_no: str | None = None

    model_config = ConfigDict(extra="forbid")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- User schemas ---

class UserResponse(BaseModel):
    user_id: int = Field(..., serialization_alias="id")
    email: str
    full_name: str
    role: str
    unit_no: str | None
    email_verified: bool
    hoa_approved: bool

    model_config = {"from_attributes": True, "populate_by_name": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
