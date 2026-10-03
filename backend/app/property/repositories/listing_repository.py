from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.property.models.listing import Listing


class ListingRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @staticmethod
    def _apply_filters(
        stmt: Select,
        *,
        status: str | None,
        unit_id: int | None,
        agent_id: int | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
    ) -> Select:
        if status is not None:
            stmt = stmt.where(Listing.status == status)
        if unit_id is not None:
            stmt = stmt.where(Listing.unit_id == unit_id)
        if agent_id is not None:
            stmt = stmt.where(Listing.agent_id == agent_id)
        if min_price is not None:
            stmt = stmt.where(Listing.price >= min_price)
        if max_price is not None:
            stmt = stmt.where(Listing.price <= max_price)
        return stmt

    async def search(
        self,
        *,
        offset: int,
        limit: int,
        status: str | None = None,
        unit_id: int | None = None,
        agent_id: int | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
    ) -> list[Listing]:
        stmt = select(Listing).order_by(Listing.created_at.desc(), Listing.listing_id.desc())
        stmt = self._apply_filters(
            stmt,
            status=status,
            unit_id=unit_id,
            agent_id=agent_id,
            min_price=min_price,
            max_price=max_price,
        )
        result = await self._db.execute(stmt.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count(
        self,
        *,
        status: str | None = None,
        unit_id: int | None = None,
        agent_id: int | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(Listing)
        stmt = self._apply_filters(
            stmt,
            status=status,
            unit_id=unit_id,
            agent_id=agent_id,
            min_price=min_price,
            max_price=max_price,
        )
        result = await self._db.execute(stmt)
        return int(result.scalar_one())

    async def get_by_id(self, listing_id: int) -> Listing | None:
        result = await self._db.execute(select(Listing).where(Listing.listing_id == listing_id))
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        unit_id: int,
        agent_id: int,
        price: Decimal,
        description: str | None,
        photo_url: str | None,
    ) -> Listing:
        listing = Listing(
            unit_id=unit_id,
            agent_id=agent_id,
            price=price,
            description=description,
            photo_url=photo_url,
            status="active",
            views=0,
        )
        self._db.add(listing)
        await self._db.commit()
        await self._db.refresh(listing)
        return listing

    async def update(self, listing: Listing, changes: dict) -> Listing:
        for field, value in changes.items():
            setattr(listing, field, value)
        await self._db.commit()
        await self._db.refresh(listing)
        return listing
