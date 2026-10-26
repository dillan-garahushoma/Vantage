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
        estate_id: int | None,
        min_size_m2: Decimal | None,
        max_size_m2: Decimal | None,
    ) -> Select:
        if bedrooms is not None:
            stmt = stmt.where(Property.bedrooms == bedrooms)
        if bathrooms is not None:
            stmt = stmt.where(Property.bathrooms == bathrooms)
        if estate_id is not None:
            stmt = stmt.where(Property.estate_id == estate_id)
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
        estate_id: int | None = None,
    ) -> list[Property]:
        stmt = select(Property).order_by(Property.unit_id)
        stmt = self._apply_filters(
            stmt,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            min_size_m2=min_size_m2,
            max_size_m2=max_size_m2,
            estate_id=estate_id,
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
        estate_id: int | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(Property)
        stmt = self._apply_filters(
            stmt,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            min_size_m2=min_size_m2,
            max_size_m2=max_size_m2,
            estate_id=estate_id,
        )
        result = await self._db.execute(stmt)
        return int(result.scalar_one())

    async def counts_for_estates(self, *, estate_ids: list[int]) -> dict[int, int]:
        """How many units each of several estates has, in one grouped query.

        The public grid needs a unit count per estate; doing it per row would be
        one query per estate on an unauthenticated endpoint.
        """
        if not estate_ids:
            return {}
        result = await self._db.execute(
            select(Property.estate_id, func.count(Property.unit_id))
            .where(Property.estate_id.in_(estate_ids))
            .group_by(Property.estate_id)
        )
        return {row[0]: int(row[1]) for row in result.all()}

    async def list_public_available(self, *, estate_id: int) -> list[Property]:
        """Published units that are currently available, ordered for stable public display."""
        result = await self._db.execute(
            select(Property)
            .where(
                Property.estate_id == estate_id,
                Property.is_public_listing.is_(True),
                Property.availability_status == "available",
            )
            .order_by(Property.unit_id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, unit_id: int) -> Property | None:
        result = await self._db.execute(select(Property).where(Property.unit_id == unit_id))
        return result.scalar_one_or_none()

    async def get_by_id_in_estate(
        self, *, unit_id: int, estate_id: int
    ) -> Property | None:
        """Return a property only when it belongs to the requested estate."""
        result = await self._db.execute(
            select(Property).where(
                Property.unit_id == unit_id,
                Property.estate_id == estate_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_unit_no(self, unit_no: str) -> Property | None:
        result = await self._db.execute(select(Property).where(Property.unit_no == unit_no))
        return result.scalar_one_or_none()

    async def get_by_unit_no_in_estate(
        self, *, estate_id: int, unit_no: str
    ) -> Property | None:
        """Return a property matching unit_no within a specific estate."""
        result = await self._db.execute(
            select(Property).where(
                Property.estate_id == estate_id,
                Property.unit_no == unit_no,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_unit_no_in_estate_ci(
        self, *, estate_id: int, unit_no: str
    ) -> Property | None:
        """Find a unit by number inside one estate, ignoring case and padding.

        The schema's uniqueness rule is case-sensitive, so two units could in
        principle differ only by case. The lowest unit id wins so the lookup is
        deterministic rather than raising; ADR-007 records that as an open
        question.
        """
        result = await self._db.execute(
            select(Property)
            .where(
                Property.estate_id == estate_id,
                func.lower(Property.unit_no) == unit_no.strip().lower(),
            )
            .order_by(Property.unit_id)
            .limit(1)
        )
        return result.scalars().first()

    async def list_unit_nos_in_estate(self, *, estate_id: int) -> set[str]:
        """Every unit number already used inside an estate."""
        result = await self._db.execute(
            select(Property.unit_no).where(Property.estate_id == estate_id)
        )
        return {row[0] for row in result.all()}

    async def create(self, **fields) -> Property:
        property_ = Property(**fields)
        self._db.add(property_)
        await self._db.commit()
        await self._db.refresh(property_)
        return property_

    async def add(self, **fields) -> Property:
        """Add a unit without committing; the bulk service commits once."""
        property_ = Property(**fields)
        self._db.add(property_)
        await self._db.flush()
        return property_

    async def flush(self) -> None:
        await self._db.flush()
