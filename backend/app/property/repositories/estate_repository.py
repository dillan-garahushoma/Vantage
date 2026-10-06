from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.property.models.estate import Estate


class EstateRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, estate_id: int) -> Estate | None:
        result = await self._db.execute(select(Estate).where(Estate.estate_id == estate_id))
        return result.scalar_one_or_none()

    async def create(self, **fields: object) -> Estate:
        estate = Estate(**fields)
        self._db.add(estate)
        await self._db.commit()
        await self._db.refresh(estate)
        return estate
