from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.common.validators import normalise_email


class ProviderInvitationAcceptRequest(BaseModel):
    token: str = Field(..., min_length=32, max_length=128)
    password: str | None = Field(default=None, min_length=8)

    model_config = ConfigDict(extra="forbid")

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: str | None) -> str | None:
        if value is not None and len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 bytes.")
        return value


class ProviderApplicationCreateRequest(BaseModel):
    estate_id: int = Field(gt=0)
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    trade: str = Field(..., min_length=1, max_length=50)
    phone: str = Field(..., min_length=5, max_length=20)
    note: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(extra="forbid")

    @field_validator("full_name", "trade", "phone", "note", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def normalise_email_address(cls, value: str) -> str:
        return normalise_email(value)


class ProviderApplicationResponse(BaseModel):
    application_id: int
    estate_id: int
    estate_name: str | None = None
    full_name: str
    email: EmailStr
    trade: str
    phone: str
    note: str | None = None
    status: str
    created_at: datetime
    reviewed_at: datetime | None = None
