from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.repositories.living_score_repository import LivingScoreRepository
from app.analytics.schemas.living_score import LivingScoreResponse
from app.core.exceptions import NotFoundException
from app.property.repositories.property_repository import PropertyRepository

_COMMUNITY_WEIGHT = Decimal("0.4")
_MAINTENANCE_WEIGHT = Decimal("0.3")
_PROVIDER_WEIGHT = Decimal("0.3")

_NEUTRAL_MAINTENANCE_SCORE = Decimal("75")
_NEUTRAL_RATING_SCORE = Decimal("70")

_PER_COMPLAINT_PENALTY = Decimal("3")
_MAX_VOLUME_PENALTY = Decimal("30")


def _clamp(value: Decimal, low: Decimal = Decimal("0"), high: Decimal = Decimal("100")) -> Decimal:
    return max(low, min(high, value))


def _round2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class LivingScoreService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = LivingScoreRepository(db)
        self._property_repo = PropertyRepository(db)

    async def get_living_score(self, unit_id: int) -> LivingScoreResponse:
        property_ = await self._property_repo.get_by_id(unit_id)
        if property_ is None:
            raise NotFoundException(f"Property with id {unit_id} was not found.")

        complaints = await self._repo.get_complaints_for_unit(unit_id)
        complaint_ids = [c.complaint_id for c in complaints]
        work_orders = await self._repo.get_work_orders_for_complaints(complaint_ids)

        community_health = self._score_community_health(complaints)
        maintenance = self._score_maintenance(work_orders)
        provider_reliability = await self._score_provider_reliability(work_orders)

        raw_score = (
            community_health * _COMMUNITY_WEIGHT
            + maintenance * _MAINTENANCE_WEIGHT
            + provider_reliability * _PROVIDER_WEIGHT
        )
        score = int(_clamp(raw_score).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

        return LivingScoreResponse(
            property_id=unit_id,
            score=score,
            community_health_factor=_round2(community_health),
            maintenance_factor=_round2(maintenance),
            provider_reliability_factor=_round2(provider_reliability),
            complaints_considered=len(complaints),
            work_orders_considered=len(work_orders),
        )

    def _score_community_health(self, complaints: list) -> Decimal:
        total = len(complaints)
        if total == 0:
            return Decimal("100")

        resolved_statuses = self._repo.resolved_statuses()
        resolved = sum(1 for c in complaints if c.status in resolved_statuses)
        resolution_rate = Decimal(resolved) / Decimal(total)

        volume_penalty = min(Decimal(total) * _PER_COMPLAINT_PENALTY, _MAX_VOLUME_PENALTY)
        return _clamp(resolution_rate * Decimal("100") - volume_penalty)

    def _score_maintenance(self, work_orders: list) -> Decimal:
        if not work_orders:
            return _NEUTRAL_MAINTENANCE_SCORE

        ratings = [wo.resident_rating for wo in work_orders if wo.resident_rating is not None]
        if ratings:
            avg_rating = Decimal(sum(ratings)) / Decimal(len(ratings))
            rating_component = _clamp(avg_rating / Decimal("5") * Decimal("100"))
        else:
            rating_component = _NEUTRAL_RATING_SCORE

        completed = sum(
            1 for wo in work_orders if wo.status == "completed" or wo.resolved_at is not None
        )
        completion_rate = Decimal(completed) / Decimal(len(work_orders))

        return _clamp(
            Decimal("0.6") * rating_component + Decimal("0.4") * completion_rate * Decimal("100")
        )

    async def _score_provider_reliability(self, work_orders: list) -> Decimal:
        provider_ids = sorted({wo.provider_id for wo in work_orders if wo.provider_id is not None})
        providers = await self._repo.get_providers_by_ids(provider_ids)

        if providers:
            rated = [Decimal(str(p.avg_rating)) for p in providers if p.avg_rating is not None]
            rating_component = (
                _clamp(sum(rated) / Decimal(len(rated)) / Decimal("5") * Decimal("100"))
                if rated
                else _NEUTRAL_RATING_SCORE
            )
            verified_ratio = Decimal(sum(1 for p in providers if p.verified)) / Decimal(len(providers))
            return _clamp(
                Decimal("0.8") * rating_component + Decimal("0.2") * verified_ratio * Decimal("100")
            )

        global_avg = await self._repo.get_global_avg_provider_rating()
        if global_avg is None:
            return _NEUTRAL_RATING_SCORE
        return _clamp(Decimal(str(global_avg)) / Decimal("5") * Decimal("100"))
