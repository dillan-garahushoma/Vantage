"""Estate-and-owner scoped persistence. No commits, calculations or updates."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.property.models.investment_scenario import InvestmentScenario


class InvestmentRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def add(self, **values) -> InvestmentScenario:
        row = InvestmentScenario(**values)
        self._db.add(row)
        await self._db.flush()
        return row

    def _owned(self, *, estate_id: int, owner_id: int):
        return select(InvestmentScenario).where(
            InvestmentScenario.estate_id == estate_id, InvestmentScenario.owner_id == owner_id,
        )

    async def get_owned(self, *, scenario_id: int, estate_id: int, owner_id: int) -> InvestmentScenario | None:
        result = await self._db.execute(self._owned(estate_id=estate_id, owner_id=owner_id).where(InvestmentScenario.scenario_id == scenario_id))
        return result.scalar_one_or_none()

    async def list_owned(self, *, estate_id: int, owner_id: int, offset: int, limit: int) -> list[InvestmentScenario]:
        query = self._owned(estate_id=estate_id, owner_id=owner_id).order_by(InvestmentScenario.created_at.desc(), InvestmentScenario.scenario_id.desc())
        result = await self._db.execute(query.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count_owned(self, *, estate_id: int, owner_id: int) -> int:
        query = select(func.count()).select_from(self._owned(estate_id=estate_id, owner_id=owner_id).subquery())
        return int((await self._db.execute(query)).scalar_one())
