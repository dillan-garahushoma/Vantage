"""Identity Pydantic schemas — request and response models."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

# Trusted provisioning choices. Public RegisterRequest narrows this to resident.
# Platform operators themselves are provisioned only through the operator CLI.
AccountType = Literal["resident", "estate_admin", "service_provider"]


class EstateSignup(BaseModel):
    """The estate an estate_admin registers in the same transaction as their account."""

    name: str = Field(..., min_length=2, max_length=160)
    suburb: str = Field(..., min_length=1, max_length=120)
    city: str = Field(..., min_length=1, max_length=120)
    province: str = Field(..., min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=5000)

    model_config = ConfigDict(extra="forbid")


class ProviderSignup(BaseModel):
    """The minimal provider profile created alongside a service_provider account.

    The profile's email and full name are the account's, so they are not accepted
    here; ``verified`` is always false and only a platform admin may change it.
    """

    trade: str = Field(..., min_length=1, max_length=50)
    phone: str = Field(..., min_length=5, max_length=20)

    model_config = ConfigDict(extra="forbid")


# --- Auth schemas ---

class ProvisionAccountRequest(BaseModel):
    """Operator-only account provisioning; clients cannot supply arbitrary roles."""

    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    phoneno: str | None = None
    unit_no: str | None = None
    account_type: AccountType = "resident"
    estate: EstateSignup | None = None
    provider: ProviderSignup | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 bytes.")
        return v

    @model_validator(mode="after")
    def validate_account_type_payload(self) -> "RegisterRequest":
        if self.account_type == "estate_admin":
            if self.estate is None:
                raise ValueError("An estate is required when account_type is estate_admin.")
            if self.provider is not None:
                raise ValueError("A provider profile is not valid for an estate_admin signup.")
        elif self.account_type == "service_provider":
            if self.provider is None:
                raise ValueError("A provider profile is required when account_type is service_provider.")
            if self.estate is not None:
                raise ValueError("An estate is not valid for a service_provider signup.")
        else:
            if self.estate is not None or self.provider is not None:
                raise ValueError("A resident signup must not carry an estate or provider object.")
        return self


class RegisterRequest(ProvisionAccountRequest):
    """Public registration creates residents; trusted roles are operator provisioned."""

    account_type: Literal['resident'] = 'resident'
    estate: None = None
    provider: None = None


class EstateRegistrationRequest(BaseModel):
    """Public onboarding for a new estate and its first HOA administrator."""

    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    phoneno: str | None = None
    estate: EstateSignup

    model_config = ConfigDict(extra="forbid")

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 bytes.")
        return value


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
