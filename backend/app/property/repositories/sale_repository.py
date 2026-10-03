from decimal import Decimal
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.property.models.sale import Sale


class SaleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def search(self, *, offset: int, limit: int, unit_id: int | None = None) -> list[Sale]:
        stmt = select(Sale).order_by(Sale.sale_date.desc(), Sale.sale_id.desc())
        if unit_id is not None:
            stmt = stmt.where(Sale.unit_id == unit_id)
        result = await self._db.execute(stmt.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count(self, *, unit_id: int | None = None) -> int:
        stmt = select(func.count()).select_from(Sale)
        if unit_id is not None:
            stmt = stmt.where(Sale.unit_id == unit_id)
        result = await self._db.execute(stmt)
        return int(result.scalar_one())

    async def get_by_id(self, sale_id: int) -> Sale | None:
        result = await self._db.execute(select(Sale).where(Sale.sale_id == sale_id))
        return result.scalar_one_or_none()

    async def create(self, *, unit_id: int, price: Decimal, sale_date: datetime) -> Sale:
        sale = Sale(unit_id=unit_id, price=price, sale_date=sale_date)
        self._db.add(sale)
        await self._db.commit()
        await self._db.refresh(sale)
        return sale
