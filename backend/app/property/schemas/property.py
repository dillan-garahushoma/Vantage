from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

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

    model_config = {"from_attributes": True, "populate_by_name": True, "serialize_by_alias": True}

class PropertyCreate(BaseModel):
    estate_id: int = Field(..., gt=0)
    unit_no: str = Field(..., min_length=1, max_length=10)
    complex_name: str = Field(..., min_length=1, max_length=255)
    street_address: str = Field(..., min_length=1, max_length=255)
    suburb: str | None = Field(default=None, max_length=255)
    size_m2: Decimal | None = Field(default=None, gt=0, max_digits=8, decimal_places=2)
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)


class BulkUnitItem(BaseModel):
    """One unit in a bulk creation request.

    ``complex_name`` and ``suburb`` are deliberately absent: both are taken from
    the estate server-side, so a caller cannot label units with a name of their
    choosing. Anything extra is rejected outright.
    """

    unit_no: str = Field(..., min_length=1, max_length=10)
    street_address: str = Field(..., min_length=1, max_length=255)
    size_m2: Decimal | None = Field(default=None, gt=0, max_digits=8, decimal_places=2)
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid")


class BulkUnitsRequest(BaseModel):
    """Create many units in one all-or-nothing request (1 to 500)."""

    units: list[BulkUnitItem] = Field(..., min_length=1, max_length=500)

    model_config = ConfigDict(extra="forbid")
