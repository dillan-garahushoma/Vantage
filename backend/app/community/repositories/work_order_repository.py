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
        estate_id: int | None,
        provider_id: int | None,
        status: str | None,
    ) -> Select:
        if complaint_id is not None:
            stmt = stmt.where(MaintenanceworkOrder.complaint_id == complaint_id)
        if estate_id is not None:
            stmt = stmt.where(MaintenanceworkOrder.estate_id == estate_id)
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
        estate_id: int | None = None,
        provider_id: int | None = None,
        status: str | None = None,
        sort: str = "-created_at",
    ) -> list[MaintenanceworkOrder]:
        sort_fields = {
            "created_at": MaintenanceworkOrder.created_at,
            "status": MaintenanceworkOrder.status,
        }
        descending = sort.startswith("-")
        field = sort_fields[sort[1:] if descending else sort]
        stmt = select(MaintenanceworkOrder).order_by(
            field.desc() if descending else field.asc(),
            MaintenanceworkOrder.work_order_id.desc(),
        )
        stmt = self._apply_filters(
            stmt,
            complaint_id=complaint_id,
            estate_id=estate_id,
            provider_id=provider_id,
            status=status,
        )
        result = await self._db.execute(stmt.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count(
        self,
        *,
        complaint_id: int | None = None,
        estate_id: int | None = None,
        provider_id: int | None = None,
        status: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(MaintenanceworkOrder)
        stmt = self._apply_filters(
            stmt,
            complaint_id=complaint_id,
            estate_id=estate_id,
            provider_id=provider_id,
            status=status,
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

    async def get_by_id_in_estate(
        self, *, work_order_id: int, estate_id: int
    ) -> MaintenanceworkOrder | None:
        result = await self._db.execute(
            select(MaintenanceworkOrder).where(
                MaintenanceworkOrder.work_order_id == work_order_id,
                MaintenanceworkOrder.estate_id == estate_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_in_estate_for_update(
        self, *, work_order_id: int, estate_id: int
    ) -> MaintenanceworkOrder | None:
        result = await self._db.execute(
            select(MaintenanceworkOrder)
            .where(
                MaintenanceworkOrder.work_order_id == work_order_id,
                MaintenanceworkOrder.estate_id == estate_id,
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_active_for_complaint(
        self, *, complaint_id: int
    ) -> MaintenanceworkOrder | None:
        result = await self._db.execute(
            select(MaintenanceworkOrder).where(
                MaintenanceworkOrder.complaint_id == complaint_id,
                MaintenanceworkOrder.status != "cancelled",
            )
        )
        return result.scalars().first()

    async def get_provider_rating_aggregate(
        self, *, provider_id: int
    ) -> tuple[Decimal | None, int]:
        result = await self._db.execute(
            select(
                func.avg(MaintenanceworkOrder.resident_rating),
                func.count(MaintenanceworkOrder.resident_rating),
            ).where(
                MaintenanceworkOrder.provider_id == provider_id,
                MaintenanceworkOrder.resident_rating.is_not(None),
            )
        )
        row = result.one()
        avg_val = Decimal(str(row[0])) if row[0] is not None else None
        count_val = int(row[1]) if row[1] is not None else 0
        return avg_val, count_val

    async def create(
        self,
        *,
        complaint_id: int,
        estate_id: int,
        provider_id: int,
        job_cost: Decimal | None,
        estimated_completion_date: datetime | None,
        commit: bool = True,
    ) -> MaintenanceworkOrder:
        work_order = MaintenanceworkOrder(
            complaint_id=complaint_id,
            estate_id=estate_id,
            provider_id=provider_id,
            job_cost=job_cost,
            estimated_completion_date=estimated_completion_date,
            status="assigned",
        )
        self._db.add(work_order)
        if commit:
            await self._db.commit()
            await self._db.refresh(work_order)
        else:
            await self._db.flush()
        return work_order

    async def save(
        self, work_order: MaintenanceworkOrder, commit: bool = True
    ) -> MaintenanceworkOrder:
        if commit:
            await self._db.commit()
            await self._db.refresh(work_order)
        else:
            await self._db.flush()
        return work_order
