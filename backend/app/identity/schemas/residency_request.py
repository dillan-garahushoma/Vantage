"""Residency-request contracts.

Three shapes:

* what a resident may send (``ResidencyRequestCreate``) - an estate *target*, a
  unit number and an optional note. The ``estate_id`` here is the estate the
  person is asking to join, not a claim of existing access; the service still
  verifies that the estate and unit exist;
* what an administrator may send to decline one (``ResidencyRequestReject``) - a
  note and nothing else. The decision itself is the endpoint, not a status field,
  so a client can never PATCH a request into ``approved``;
* what either side may read back (``ResidencyRequestResponse``), which carries the
  applicant's contact details because an administrator has to be able to identify
  the person, and the resident's own request is their own data.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.identity.models.estate_residency_request import (
    NOTE_MAX_LENGTH,
    UNIT_NO_MAX_LENGTH,
)


class ResidencyRequestCreate(BaseModel):
    """A resident's request to be admitted to one unit of one estate."""

    estate_id: int = Field(..., gt=0)
    unit_no: str = Field(..., min_length=1, max_length=UNIT_NO_MAX_LENGTH)
    note: str | None = Field(default=None, max_length=NOTE_MAX_LENGTH)

    model_config = ConfigDict(extra="forbid")

    @field_validator("unit_no", "note", mode="before")
    @classmethod
    def strip_whitespace(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ResidencyRequestReject(BaseModel):
    """The optional reason an administrator declining a request may record."""

    note: str | None = Field(default=None, max_length=NOTE_MAX_LENGTH)

    model_config = ConfigDict(extra="forbid")

    @field_validator("note", mode="before")
    @classmethod
    def strip_whitespace(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ResidencyRequestResponse(BaseModel):
    """One residency request, as the admin queue or the resident's own list shows it."""

    request_id: int
    estate_id: int
    # Resolved from the estate row and included so the resident's cross-estate
    # list reads correctly; the admin list is already estate-scoped.
    estate_name: str | None = None
    unit_no: str
    status: str
    applicant_name: str
    applicant_email: str
    applicant_phone: str | None = None
    note: str | None = None
    created_at: datetime
    decided_at: datetime | None = None
    decision_note: str | None = None


class PendingResidencyCountResponse(BaseModel):
    """The badge number for the admin navigation."""

    pending: int
