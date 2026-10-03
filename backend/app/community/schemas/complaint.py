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
    is_anonymous: bool = False


class ComplaintStatusUpdate(BaseModel):
    status: ComplaintStatus
    assigned_to: str | None = Field(default=None, max_length=100)


class ComplaintResponse(BaseModel):
    complaint_id: int = Field(..., serialization_alias="id")
    # hidden (null) for anonymous complaints unless the viewer is the author
    user_id: int | None
    unit_id: int
    category: str
    description: str
    is_anonymous: bool | None
    status: str | None
    assigned_to: str | None
    resolved_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True, "populate_by_name": True}


class PaginatedComplaintsResponse(BaseModel):
    count: int
    page: int
    page_size: int
    complaints: list[ComplaintResponse]
