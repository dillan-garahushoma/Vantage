from datetime import datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.community.models.announcement import Announcement


class AnnouncementRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @staticmethod
    def _only_active(stmt: Select, now: datetime) -> Select:
        return stmt.where(or_(Announcement.expires_at.is_(None), Announcement.expires_at > now))

    async def search(
        self, *, offset: int, limit: int, include_expired: bool, now: datetime
    ) -> list[Announcement]:
        stmt = select(Announcement).order_by(
            Announcement.created_at.desc(), Announcement.announcement_id.desc()
        )
        if not include_expired:
            stmt = self._only_active(stmt, now)
        result = await self._db.execute(stmt.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count(self, *, include_expired: bool, now: datetime) -> int:
        stmt = select(func.count()).select_from(Announcement)
        if not include_expired:
            stmt = self._only_active(stmt, now)
        result = await self._db.execute(stmt)
        return int(result.scalar_one())

    async def get_by_id(self, announcement_id: int) -> Announcement | None:
        result = await self._db.execute(
            select(Announcement).where(Announcement.announcement_id == announcement_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self, *, title: str, message: str, created_by: int, expires_at: datetime | None
    ) -> Announcement:
        announcement = Announcement(
            title=title, message=message, created_by=created_by, expires_at=expires_at
        )
        self._db.add(announcement)
        await self._db.commit()
        await self._db.refresh(announcement)
        return announcement

    async def save(self, announcement: Announcement) -> Announcement:
        await self._db.commit()
        await self._db.refresh(announcement)
        return announcement

    async def delete(self, announcement: Announcement) -> None:
        await self._db.delete(announcement)
        await self._db.commit()
