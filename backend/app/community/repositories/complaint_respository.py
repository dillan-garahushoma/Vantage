from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.community.models.complaint import Complaint


class ComplaintRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_all(self) -> list[Complaint]:
        result = await self._db.execute(select(Complaint))
        return list(result.scalars().all())

    @staticmethod
    def _apply_filters(
        stmt: Select,
        *,
        user_id: int | None,
        unit_id: int | None,
        status: str | None,
        category: str | None,
    ) -> Select:
        if user_id is not None:
            stmt = stmt.where(Complaint.user_id == user_id)
        if unit_id is not None:
            stmt = stmt.where(Complaint.unit_id == unit_id)
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
        status: str | None = None,
        category: str | None = None,
    ) -> list[Complaint]:
        stmt = select(Complaint).order_by(Complaint.created_at.desc(), Complaint.complaint_id.desc())
        stmt = self._apply_filters(
            stmt, user_id=user_id, unit_id=unit_id, status=status, category=category
        )
        result = await self._db.execute(stmt.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count(
        self,
        *,
        user_id: int | None = None,
        unit_id: int | None = None,
        status: str | None = None,
        category: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(Complaint)
        stmt = self._apply_filters(
            stmt, user_id=user_id, unit_id=unit_id, status=status, category=category
        )
        result = await self._db.execute(stmt)
        return int(result.scalar_one())

    async def get_by_id(self, complaint_id: int) -> Complaint | None:
        result = await self._db.execute(
            select(Complaint).where(Complaint.complaint_id == complaint_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: int,
        unit_id: int,
        category: str,
        description: str,
        is_anonymous: bool,
    ) -> Complaint:
        complaint = Complaint(
            user_id=user_id,
            unit_id=unit_id,
            category=category,
            description=description,
            is_anonymous=is_anonymous,
            status="submitted",
        )
        self._db.add(complaint)
        await self._db.commit()
        await self._db.refresh(complaint)
        return complaint

    async def save(self, complaint: Complaint) -> Complaint:
        await self._db.commit()
        await self._db.refresh(complaint)
        return complaint
