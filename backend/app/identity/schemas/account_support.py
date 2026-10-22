from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, StringConstraints, field_validator


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    notification_id: int = Field(serialization_alias='id')
    estate_id: int
    kind: str
    resource_id: int
    created_at: datetime
    read_at: datetime | None


class PreferenceResponse(BaseModel):
    model_config = ConfigDict(extra='forbid', from_attributes=True)
    maintenance_notifications: bool = True


class RecoveryRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: EmailStr


class RecoveryConfirm(BaseModel):
    model_config = ConfigDict(extra='forbid')
    token: Annotated[str, StringConstraints(min_length=32, max_length=128)]
    password: SecretStr

    @field_validator('password')
    @classmethod
    def password_length(cls, value):
        password = value.get_secret_value()
        if len(password) < 8 or len(password.encode('utf-8')) > 72:
            raise ValueError('Password must have at least 8 characters and at most 72 bytes.')
        return value


class MessageResponse(BaseModel):
    message: str
