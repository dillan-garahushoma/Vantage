from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ComplaintStatus
from app.community.models.complaint import Complaint
from app.community.models.maintenance_work_order import MaintenanceworkOrder
from app.providers.models.service_provider import ServiceProvider


class LivingScoreRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_complaints_for_unit(self, unit_id: int) -> list[Complaint]:
        result = await self._db.execute(
            select(Complaint).where(Complaint.unit_id == unit_id)
        )
        return list(result.scalars().all())

    async def get_work_orders_for_complaints(
        self, complaint_ids: list[int]
    ) -> list[MaintenanceworkOrder]:
        if not complaint_ids:
            return []
        result = await self._db.execute(
            select(MaintenanceworkOrder).where(
                MaintenanceworkOrder.complaint_id.in_(complaint_ids)
            )
        )
        return list(result.scalars().all())

    async def get_providers_by_ids(self, provider_ids: list[int]) -> list[ServiceProvider]:
        if not provider_ids:
            return []
        result = await self._db.execute(
            select(ServiceProvider).where(ServiceProvider.provider_id.in_(provider_ids))
        )
        return list(result.scalars().all())

    async def get_global_avg_provider_rating(self) -> float | None:
        result = await self._db.execute(select(func.avg(ServiceProvider.avg_rating)))
        avg = result.scalar_one_or_none()
        return float(avg) if avg is not None else None

    @staticmethod
    def resolved_statuses() -> tuple[str, ...]:
        return (ComplaintStatus.resolved.value, ComplaintStatus.closed.value)
