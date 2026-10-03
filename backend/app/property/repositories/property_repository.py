from decimal import Decimal
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.property.models.property import Property

class PropertyRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    def _apply_filters(
        self,
        stmt: Select,
        *,
        bedrooms: int | None,
        bathrooms: int | None,
        min_size_m2: Decimal | None,
        max_size_m2: Decimal | None,
    ) -> Select:
        if bedrooms is not None:
            stmt = stmt.where(Property.bedrooms == bedrooms)
        if bathrooms is not None:
            stmt = stmt.where(Property.bathrooms == bathrooms)
        if min_size_m2 is not None:
            stmt = stmt.where(Property.size_m2 >= min_size_m2)
        if max_size_m2 is not None:
            stmt = stmt.where(Property.size_m2 <= max_size_m2)
        return stmt

    async def search(
        self,
        *,
        offset: int,
        limit: int,
        bedrooms: int | None = None,
        bathrooms: int | None = None,
        min_size_m2: Decimal | None = None,
        max_size_m2: Decimal | None = None,
    ) -> list[Property]:
        stmt = select(Property).order_by(Property.unit_id)
        stmt = self._apply_filters(
            stmt,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            min_size_m2=min_size_m2,
            max_size_m2=max_size_m2,
        )
        result = await self._db.execute(stmt.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count(
        self,
        *,
        bedrooms: int | None = None,
        bathrooms: int | None = None,
        min_size_m2: Decimal | None = None,
        max_size_m2: Decimal | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(Property)
        stmt = self._apply_filters(
            stmt,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            min_size_m2=min_size_m2,
            max_size_m2=max_size_m2,
        )
        result = await self._db.execute(stmt)
        return int(result.scalar_one())

    async def get_by_id(self, unit_id: int) -> Property | None:
        result = await self._db.execute(select(Property).where(Property.unit_id == unit_id))
        return result.scalar_one_or_none()

    async def get_by_unit_no(self, unit_no: str) -> Property | None:
        result = await self._db.execute(select(Property).where(Property.unit_no == unit_no))
        return result.scalar_one_or_none()

    async def create(self, **fields) -> Property:
        property_ = Property(**fields)
        self._db.add(property_)
        await self._db.commit()
        await self._db.refresh(property_)
        return property_
