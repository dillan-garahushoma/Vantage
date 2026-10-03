"""Providers domain entities — pure business concepts decoupled from the ORM."""
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class ServiceProviderEntity:
    provider_id: int
    full_name: str
    trade: str
    phone: str
    email: str
    avg_rating: Decimal | None
    verified: bool
    emergency_available: bool
