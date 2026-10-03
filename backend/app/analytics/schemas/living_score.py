from decimal import Decimal

from pydantic import BaseModel


class LivingScoreResponse(BaseModel):
    property_id: int
    score: int
    community_health_factor: Decimal
    maintenance_factor: Decimal
    provider_reliability_factor: Decimal
    complaints_considered: int
    work_orders_considered: int
