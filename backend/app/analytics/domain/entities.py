"""Analytics domain entities — pure business concepts decoupled from the ORM."""
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class LivingScoreEntity:
    property_id: int
    score: int
    community_health_factor: Decimal
    maintenance_factor: Decimal
    provider_reliability_factor: Decimal
