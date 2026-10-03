from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.common.datetime_utils import ensure_utc


class SaleCreate(BaseModel):
    unit_id: int = Field(..., ge=1)
    price: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    sale_date: datetime

    @field_validator("sale_date")
    @classmethod
    def _sale_date_utc(cls, value: datetime) -> datetime:
        return ensure_utc(value)


class SaleResponse(BaseModel):
    sale_id: int = Field(..., serialization_alias="id")
    unit_id: int
    price: Decimal
    sale_date: datetime
    created_at: datetime | None

    model_config = {"from_attributes": True, "populate_by_name": True}


class PaginatedSalesResponse(BaseModel):
    count: int
    page: int
    page_size: int
    sales: list[SaleResponse]
