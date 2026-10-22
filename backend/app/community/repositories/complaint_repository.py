from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.community.models.complaint import Complaint
from app.community.models.complaint_event import ComplaintEvent


class ComplaintRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def lock_in_estate(self, *, complaint_id: int, estate_id: int):
        return (await self._db.execute(select(Complaint).where(
            Complaint.complaint_id == complaint_id, Complaint.estate_id == estate_id)
            .with_for_update())).scalar_one_or_none()

    async def get_stats_aggregates(self, *, estate_id: int) -> dict:
        total_res = await self._db.execute(
            select(func.count(Complaint.complaint_id)).where(Complaint.estate_id == estate_id)
        )
        total = int(total_res.scalar_one())

        status_res = await self._db.execute(
            select(Complaint.status, func.count(Complaint.complaint_id))
            .where(Complaint.estate_id == estate_id)
            .group_by(Complaint.status)
        )
        by_status = {row[0]: int(row[1]) for row in status_res.all() if row[0] is not None}

        cat_res = await self._db.execute(
            select(Complaint.category, func.count(Complaint.complaint_id))
            .where(Complaint.estate_id == estate_id)
            .group_by(Complaint.category)
        )
        by_category = {row[0]: int(row[1]) for row in cat_res.all() if row[0] is not None}

        resolved_count = by_status.get("resolved", 0) + by_status.get("rated", 0)
        time_diff = func.extract("epoch", Complaint.resolved_at - Complaint.created_at) / 3600
        avg_res = await self._db.execute(
            select(func.avg(time_diff)).where(
                Complaint.estate_id == estate_id,
                Complaint.status.in_(["resolved", "rated"]),
                Complaint.resolved_at.is_not(None),
                Complaint.created_at.is_not(None),
            )
        )
        avg_hours_val = avg_res.scalar_one_or_none()
        avg_hours = (
            Decimal(str(avg_hours_val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if avg_hours_val is not None
            else None
        )

        resolution_rate_pct = (
            (Decimal(resolved_count) / Decimal(total) * Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if total > 0
            else Decimal("0.00")
        )

        return {
            "total": total,
            "by_status": by_status,
            "by_category": by_category,
            "resolution_rate_pct": resolution_rate_pct,
            "avg_resolution_hours": avg_hours,
        }

    @staticmethod
    def _apply_filters(
        stmt: Select,
        *,
        user_id: int | None,
        unit_id: int | None,
        estate_id: int | None,
        status: str | None,
        category: str | None,
    ) -> Select:
        if user_id is not None:
            stmt = stmt.where(Complaint.user_id == user_id)
        if unit_id is not None:
            stmt = stmt.where(Complaint.unit_id == unit_id)
        if estate_id is not None:
            stmt = stmt.where(Complaint.estate_id == estate_id)
        if status is not None:
            stmt = stmt.where(Complaint.status == status)
        if category is not None:
            stmt = stmt.where(Complaint.category == category)
        return stmt

    async def search(
        self,
        *,
        offset: int,
        limit: int,
        user_id: int | None = None,
        unit_id: int | None = None,
        estate_id: int | None = None,
        status: str | None = None,
        category: str | None = None,
        sort: str = "-created_at",
    ) -> list[Complaint]:
        sort_fields = {
            "created_at": Complaint.created_at,
            "priority": Complaint.priority,
            "status": Complaint.status,
        }
        descending = sort.startswith("-")
        field = sort_fields[sort[1:] if descending else sort]
        stmt = select(Complaint).order_by(
            field.desc() if descending else field.asc(),
            Complaint.complaint_id.desc(),
        )
        stmt = self._apply_filters(
            stmt,
            user_id=user_id,
            unit_id=unit_id,
            estate_id=estate_id,
            status=status,
            category=category,
        )
        result = await self._db.execute(stmt.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count(
        self,
        *,
        user_id: int | None = None,
        unit_id: int | None = None,
        estate_id: int | None = None,
        status: str | None = None,
        category: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(Complaint)
        stmt = self._apply_filters(
            stmt,
            user_id=user_id,
            unit_id=unit_id,
            estate_id=estate_id,
            status=status,
            category=category,
        )
        result = await self._db.execute(stmt)
        return int(result.scalar_one())

    async def get_by_id(self, complaint_id: int) -> Complaint | None:
        result = await self._db.execute(
            select(Complaint).where(Complaint.complaint_id == complaint_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_in_estate(self, *, complaint_id: int, estate_id: int) -> Complaint | None:
        result = await self._db.execute(
            select(Complaint).where(
                Complaint.complaint_id == complaint_id,
                Complaint.estate_id == estate_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_events(self, *, complaint_id: int) -> list[ComplaintEvent]:
        result = await self._db.execute(
            select(ComplaintEvent)
            .where(ComplaintEvent.complaint_id == complaint_id)
            .order_by(ComplaintEvent.occurred_at, ComplaintEvent.event_id)
        )
        return list(result.scalars().all())

    async def create(
        self,
        *,
        user_id: int,
        unit_id: int,
        estate_id: int,
        category: str,
        description: str,
        priority: str,
        is_anonymous: bool,
        commit: bool = True,
    ) -> Complaint:
        complaint = Complaint(
            user_id=user_id,
            unit_id=unit_id,
            estate_id=estate_id,
            category=category,
            description=description,
            priority=priority,
            is_anonymous=is_anonymous,
            status="submitted",
        )
        self._db.add(complaint)
        await self._db.flush()
        self._db.add(
            ComplaintEvent(
                complaint_id=complaint.complaint_id,
                estate_id=estate_id,
                actor_user_id=user_id,
                event_type="submitted",
                to_status="submitted",
            )
        )
        if commit:
            await self._db.commit()
            await self._db.refresh(complaint)
        else:
            await self._db.flush()
        return complaint

    async def save(self, complaint: Complaint, commit: bool = True) -> Complaint:
        if commit:
            await self._db.commit()
            await self._db.refresh(complaint)
        else:
            await self._db.flush()
        return complaint

    async def record_transition(
        self,
        *,
        complaint: Complaint,
        actor_user_id: int,
        from_status: str,
        to_status: str,
        note: str | None,
        commit: bool = True,
    ) -> Complaint:
        self._db.add(
            ComplaintEvent(
                complaint_id=complaint.complaint_id,
                estate_id=complaint.estate_id,
                actor_user_id=actor_user_id,
                event_type=to_status,
                from_status=from_status,
                to_status=to_status,
                note=note,
            )
        )
        if commit:
            await self._db.commit()
            await self._db.refresh(complaint)
        else:
            await self._db.flush()
        return complaint
