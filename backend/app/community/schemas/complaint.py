from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.common.enums import ComplaintStatus
from app.community.domain.triage_vocabulary import Category, Priority


class ComplaintStatsResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    by_category: dict[str, int]
    resolution_rate_pct: Decimal
    avg_resolution_hours: Decimal | None


class ComplaintCreate(BaseModel):
    """What a resident or HOA admin files. The category and priority are the
    fixed vocabulary, so the contract publishes the allowed values (BE-1).

    The response DTOs below deliberately stay plain strings: rows filed before
    the vocabulary existed may carry a free-text category, and they must still
    read back.
    """

    unit_id: int = Field(..., ge=1)
    category: Category
    description: str = Field(..., min_length=5, max_length=5000)
    priority: Priority = "normal"
    is_anonymous: bool = False


class ComplaintStatusUpdate(BaseModel):
    status: ComplaintStatus
    note: str | None = Field(default=None, max_length=2000)


class ComplaintEventResponse(BaseModel):
    event_id: int = Field(..., serialization_alias="id")
    actor_user_id: int | None
    event_type: str
    from_status: str | None
    to_status: str | None
    note: str | None
    occurred_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True, "serialize_by_alias": True}


class ComplaintResponse(BaseModel):
    complaint_id: int = Field(..., serialization_alias="id")
    # hidden (null) for anonymous complaints unless the viewer is the author
    user_id: int | None
    estate_id: int | None
    unit_id: int
    category: str
    description: str
    priority: str
    is_anonymous: bool | None
    status: str | None
    assigned_to: str | None
    reviewed_at: datetime | None
    assigned_at: datetime | None
    started_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True, "populate_by_name": True, "serialize_by_alias": True}
