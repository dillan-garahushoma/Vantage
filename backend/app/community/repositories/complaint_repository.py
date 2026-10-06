from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.community.models.complaint import Complaint
from app.community.models.complaint_event import ComplaintEvent


class ComplaintRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_all(self, *, estate_id: int) -> list[Complaint]:
        result = await self._db.execute(
            select(Complaint).where(Complaint.estate_id == estate_id)
        )
        return list(result.scalars().all())

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
    ) -> list[Complaint]:
        stmt = select(Complaint).order_by(Complaint.created_at.desc(), Complaint.complaint_id.desc())
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
        await self._db.commit()
        await self._db.refresh(complaint)
        return complaint

    async def save(self, complaint: Complaint) -> Complaint:
        await self._db.commit()
        await self._db.refresh(complaint)
        return complaint

    async def record_transition(
        self,
        *,
        complaint: Complaint,
        actor_user_id: int,
        from_status: str,
        to_status: str,
        note: str | None,
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
        await self._db.commit()
        await self._db.refresh(complaint)
        return complaint
