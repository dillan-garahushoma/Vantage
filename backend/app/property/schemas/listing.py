from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.common.enums import ListingStatus


class ListingCreate(BaseModel):
    unit_id: int = Field(..., ge=1)
    price: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, max_length=5000)
    photo_url: str | None = None


class ListingUpdate(BaseModel):
    price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, max_length=5000)
    photo_url: str | None = None
    status: ListingStatus | None = None


class ListingResponse(BaseModel):
    listing_id: int = Field(..., serialization_alias="id")
    unit_id: int
    agent_id: int
    price: Decimal
    description: str | None
    photo_url: str | None
    status: str | None
    views: int | None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True, "populate_by_name": True}


class PaginatedListingsResponse(BaseModel):
    count: int
    page: int
    page_size: int
    listings: list[ListingResponse]
