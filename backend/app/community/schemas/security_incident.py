from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.common.datetime_utils import ensure_utc, utcnow
from app.community.domain.incident_vocabulary import CATEGORIES, SEVERITIES, STATUSES

# Built from the vocabulary so a value can never be added in one place only.
IncidentCategory = Literal[*CATEGORIES]
IncidentSeverity = Literal[*SEVERITIES]
IncidentStatus = Literal[*STATUSES]

# A client clock a few minutes ahead of the server is normal; hours are not.
_MAX_CLOCK_SKEW = timedelta(minutes=5)


class IncidentCreate(BaseModel):
    """What an HOA admin may send when recording an incident.

    ``estate_id``, ``status`` and ``created_by`` are deliberately absent: the
    estate comes from an authorized membership, the status always starts at
    ``open`` and the author is the logged-in admin. Unknown fields are refused
    rather than silently dropped.
    """

    category: IncidentCategory
    severity: IncidentSeverity
    occurred_at: datetime
    property_id: int | None = Field(default=None, ge=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("occurred_at")
    @classmethod
    def _not_in_the_future(cls, value: datetime) -> datetime:
        value = ensure_utc(value)
        assert value is not None
        if value > utcnow() + _MAX_CLOCK_SKEW:
            raise ValueError("occurred_at cannot be in the future.")
        return value


class IncidentUpdate(BaseModel):
    """The only patchable fields.

    ``category``, ``occurred_at``, ``estate_id`` and ``property_id`` are
    immutable, and ``status`` moves only along the allowed transitions (the
    service owns those). Because unknown fields are refused, an attempt to patch
    an immutable field is a 422 rather than a silent no-op.
    """

    severity: IncidentSeverity | None = None
    status: IncidentStatus | None = None
    resolution_notes: str | None = Field(default=None, max_length=2000)

    model_config = ConfigDict(extra="forbid")


class IncidentResponse(BaseModel):
    """One incident. The three admin-only fields are null for other members."""

    incident_id: int = Field(..., serialization_alias="id")
    estate_id: int
    category: str
    severity: str
    status: str
    occurred_at: datetime
    resolved_at: datetime | None
    # hidden (null) for everyone who is not an estate admin
    property_id: int | None
    resolution_notes: str | None
    created_by: int | None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "serialize_by_alias": True,
    }
