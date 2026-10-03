from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.common.datetime_utils import ensure_utc
from app.common.enums import WorkOrderStatus


class WorkOrderCreate(BaseModel):
    complaint_id: int = Field(..., ge=1)
    provider_id: int = Field(..., ge=1)
    job_cost: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    estimated_completion_date: datetime | None = None

    @field_validator("estimated_completion_date")
    @classmethod
    def _utc(cls, value: datetime | None) -> datetime | None:
        return ensure_utc(value)


class WorkOrderUpdate(BaseModel):
    status: WorkOrderStatus | None = None
    job_cost: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    completion_notes: str | None = Field(default=None, max_length=5000)
    estimated_completion_date: datetime | None = None

    @field_validator("estimated_completion_date")
    @classmethod
    def _utc(cls, value: datetime | None) -> datetime | None:
        return ensure_utc(value)


class WorkOrderRating(BaseModel):
    rating: int = Field(..., ge=1, le=5)


class WorkOrderResponse(BaseModel):
    work_order_id: int = Field(..., serialization_alias="id")
    complaint_id: int
    provider_id: int
    assigned_at: datetime | None
    resolved_at: datetime | None
    job_cost: Decimal | None
    resident_rating: int | None
    completion_notes: str | None
    status: str | None
    estimated_completion_date: datetime | None
    actual_completion_date: datetime | None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True, "populate_by_name": True}


class PaginatedWorkOrdersResponse(BaseModel):
    count: int
    page: int
    page_size: int
    work_orders: list[WorkOrderResponse]
