"""Property domain entities — pure business concepts decoupled from the ORM."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class PropertyEntity:
    unit_id: int
    unit_no: str
    complex_name: str
    street_address: str
    suburb: str | None
    size_m2: Decimal | None
    bedrooms: int | None
    bathrooms: int | None


@dataclass
class ValuationResult:
    unit_id: int
    predicted_market_value: Decimal
    rental_yield_pct: Decimal
    ten_year_roi: Decimal
    confidence_score: Decimal
    calculated_at: datetime
