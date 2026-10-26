from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PropertyResponse(BaseModel):
    unit_id: int = Field(..., serialization_alias="id")
    estate_id: int | None
    unit_no: str
    complex_name: str
    street_address: str
    suburb: str | None
    size_m2: Decimal | None
    bedrooms: int | None
    bathrooms: int | None
    listing_title: str | None
    listing_description: str | None
    amenities: list[str]
    is_public_listing: bool
    availability_status: str

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "serialize_by_alias": True,
    }


class PropertyCreate(BaseModel):
    estate_id: int = Field(..., gt=0)
    unit_no: str = Field(..., min_length=1, max_length=10)
    street_address: str = Field(..., min_length=1, max_length=255)
    suburb: str | None = Field(default=None, max_length=255)
    size_m2: Decimal | None = Field(default=None, gt=0, max_digits=8, decimal_places=2)
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)


class BulkUnitItem(BaseModel):
    """One unit in a bulk creation request; complex and suburb come from the estate."""

    unit_no: str = Field(..., min_length=1, max_length=10)
    street_address: str = Field(..., min_length=1, max_length=255)
    size_m2: Decimal | None = Field(default=None, gt=0, max_digits=8, decimal_places=2)
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid")


class PropertyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    street_address: str | None = Field(default=None, min_length=1, max_length=255)
    size_m2: Decimal | None = Field(default=None, gt=0, max_digits=8, decimal_places=2)
    bedrooms: int | None = Field(default=None, ge=0, le=100)
    bathrooms: int | None = Field(default=None, ge=0, le=100)
    listing_title: str | None = Field(default=None, min_length=2, max_length=160)
    listing_description: str | None = Field(default=None, max_length=4000)
    amenities: list[str] = Field(default_factory=list, max_length=20)
    is_public_listing: bool | None = None
    availability_status: Literal["available", "occupied", "not_available"] | None = None

    @field_validator("listing_title", "listing_description", mode="before")
    @classmethod
    def trim_listing_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("amenities")
    @classmethod
    def clean_amenities(cls, values: list[str]) -> list[str]:
        result = []
        seen = set()
        for item in values:
            clean = item.strip()
            if not clean:
                continue
            if len(clean) > 60:
                raise ValueError("Each amenity must be 60 characters or fewer.")
            key = clean.casefold()
            if key not in seen:
                result.append(clean)
                seen.add(key)
        if len(result) > 20:
            raise ValueError("Choose no more than 20 amenities.")
        return result


class BulkUnitsRequest(BaseModel):
    """Create many units in one all-or-nothing request (1 to 500)."""

    units: list[BulkUnitItem] = Field(..., min_length=1, max_length=500)

    model_config = ConfigDict(extra="forbid")
