"""Membership request and response contracts.

These are the only shapes a resident or an estate admin ever sees about
membership: the join request and its narrow confirmation, and the member list an
admin manages. No DTO here carries another member's data in a join response, and
none carries a join code anywhere except the join request itself.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MembershipJoinRequest(BaseModel):
    """A resident's join request: the shared code plus their unit number.

    The code is normalised again inside the service (case, spaces and hyphens are
    all tolerated), so this DTO only trims it and enforces a length.
    """

    code: str = Field(..., min_length=1, max_length=32)
    unit_no: str = Field(..., min_length=1, max_length=10)

    model_config = ConfigDict(extra="forbid")

    @field_validator("code", "unit_no", mode="before")
    @classmethod
    def strip_whitespace(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class MembershipJoinResponse(BaseModel):
    """The narrow confirmation a resident gets after joining.

    Deliberately tiny: the estate they can now act in, the unit the membership is
    attached to, and the role. Never the code, never another member, never any
    other estate's data.
    """

    estate_id: int
    estate_name: str
    unit_id: int
    unit_no: str
    role: str


class MembershipResponse(BaseModel):
    """One row of the admin's member list."""

    membership_id: int
    role: str
    full_name: str | None = None

    email: str | None = None
    unit_no: str | None = None
    joined_at: datetime | None = None


class MembershipUnitUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    property_id: int = Field(gt=0, le=2147483647)
