from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.common.enums import ComplaintStatus


class ComplaintStatsResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    by_category: dict[str, int]
    resolution_rate_pct: Decimal
    avg_resolution_hours: Decimal | None


class ComplaintCreate(BaseModel):
    unit_id: int = Field(..., ge=1)
    category: str = Field(..., min_length=2, max_length=50)
    description: str = Field(..., min_length=5, max_length=5000)
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    is_anonymous: bool = False


class ComplaintStatusUpdate(BaseModel):
    status: ComplaintStatus
    assigned_to: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=2000)


class ComplaintEventResponse(BaseModel):
    event_id: int = Field(..., serialization_alias="id")
    actor_user_id: int | None
    event_type: str
    from_status: str | None
    to_status: str | None
    note: str | None
    occurred_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


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

    model_config = {"from_attributes": True, "populate_by_name": True}


class PaginatedComplaintsResponse(BaseModel):
    count: int
    page: int
    page_size: int
    complaints: list[ComplaintResponse]
