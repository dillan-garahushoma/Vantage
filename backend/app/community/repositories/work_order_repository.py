from decimal import Decimal
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.community.models.maintenance_work_order import MaintenanceworkOrder


class WorkOrderRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @staticmethod
    def _apply_filters(
        stmt: Select,
        *,
        complaint_id: int | None,
        provider_id: int | None,
        status: str | None,
    ) -> Select:
        if complaint_id is not None:
            stmt = stmt.where(MaintenanceworkOrder.complaint_id == complaint_id)
        if provider_id is not None:
            stmt = stmt.where(MaintenanceworkOrder.provider_id == provider_id)
        if status is not None:
            stmt = stmt.where(MaintenanceworkOrder.status == status)
        return stmt

    async def search(
        self,
        *,
        offset: int,
        limit: int,
        complaint_id: int | None = None,
        provider_id: int | None = None,
        status: str | None = None,
    ) -> list[MaintenanceworkOrder]:
        stmt = select(MaintenanceworkOrder).order_by(MaintenanceworkOrder.work_order_id.desc())
        stmt = self._apply_filters(
            stmt, complaint_id=complaint_id, provider_id=provider_id, status=status
        )
        result = await self._db.execute(stmt.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count(
        self,
        *,
        complaint_id: int | None = None,
        provider_id: int | None = None,
        status: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(MaintenanceworkOrder)
        stmt = self._apply_filters(
            stmt, complaint_id=complaint_id, provider_id=provider_id, status=status
        )
        result = await self._db.execute(stmt)
        return int(result.scalar_one())

    async def get_by_id(self, work_order_id: int) -> MaintenanceworkOrder | None:
        result = await self._db.execute(
            select(MaintenanceworkOrder).where(
                MaintenanceworkOrder.work_order_id == work_order_id
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        complaint_id: int,
        provider_id: int,
        job_cost: Decimal | None,
        estimated_completion_date: datetime | None,
    ) -> MaintenanceworkOrder:
        work_order = MaintenanceworkOrder(
            complaint_id=complaint_id,
            provider_id=provider_id,
            job_cost=job_cost,
            estimated_completion_date=estimated_completion_date,
            status="assigned",
        )
        self._db.add(work_order)
        await self._db.commit()
        await self._db.refresh(work_order)
        return work_order

    async def save(self, work_order: MaintenanceworkOrder) -> MaintenanceworkOrder:
        await self._db.commit()
        await self._db.refresh(work_order)
        return work_order
