from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.property.models.estate import Estate


class EstateRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @staticmethod
    def scoring_statement(
        *, estate_id: int | None = None, include_demo: bool = False
    ) -> Select:
        """Which estates a bulk recalculation should visit, oldest id first.

        Real estates only unless ``include_demo`` is set: a seeded demonstration
        estate is not a customer's operations. Exposed as a pure function so the
        selection rule is testable without a database.
        """
        stmt = select(Estate.estate_id).order_by(Estate.estate_id)
        if estate_id is not None:
            stmt = stmt.where(Estate.estate_id == estate_id)
        if not include_demo:
            stmt = stmt.where(Estate.is_demo.is_(False))
        return stmt

    async def list_ids_for_scoring(
        self, *, estate_id: int | None = None, include_demo: bool = False
    ) -> list[int]:
        """The ids a bulk recalculation should visit."""
        result = await self._db.execute(
            self.scoring_statement(estate_id=estate_id, include_demo=include_demo)
        )
        return [row[0] for row in result.all()]

    @staticmethod
    def public_statement(*, q: str | None = None) -> Select:
        """The estates the public directory may show, in a stable order.

        Explicit publication is the visibility gate. ``is_demo`` describes the
        origin of score data; it must not hide an estate its administrator has
        published. Demo fixtures remain private by setting ``is_public`` false.
        A pure function so the rule is testable without a database.
        """
        stmt = select(Estate).where(Estate.is_public.is_(True))
        if q:
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(
                Estate.name.ilike(pattern)
                | Estate.suburb.ilike(pattern)
                | Estate.city.ilike(pattern)
                | Estate.province.ilike(pattern)
            )
        return stmt.order_by(Estate.name.asc(), Estate.estate_id.asc())

    async def list_public(
        self, *, offset: int, limit: int, q: str | None = None
    ) -> list[Estate]:
        result = await self._db.execute(
            self.public_statement(q=q).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def count_public(self, *, q: str | None = None) -> int:
        # The public statement carries an ORDER BY for paging; a count that keeps
        # it is invalid SQL (PostgreSQL requires ordered columns in GROUP BY), so
        # it is dropped here rather than duplicated into a second statement.
        statement = (
            self.public_statement(q=q)
            .order_by(None)
            .with_only_columns(func.count(Estate.estate_id))
        )
        result = await self._db.execute(statement)
        return int(result.scalar_one())

    async def get_by_id(self, estate_id: int) -> Estate | None:
        result = await self._db.execute(select(Estate).where(Estate.estate_id == estate_id))
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Estate | None:
        result = await self._db.execute(select(Estate).where(Estate.name == name))
        return result.scalar_one_or_none()

    async def get_many_by_ids(self, estate_ids: list[int]) -> dict[int, Estate]:
        """Fetch several estates at once, keyed by id."""
        if not estate_ids:
            return {}
        result = await self._db.execute(
            select(Estate).where(Estate.estate_id.in_(estate_ids))
        )
        return {estate.estate_id: estate for estate in result.scalars().all()}

    async def create(self, **fields: object) -> Estate:
        estate = Estate(**fields)
        self._db.add(estate)
        await self._db.commit()
        await self._db.refresh(estate)
        return estate

    async def add(self, **fields: object) -> Estate:
        """Add an estate without committing; the signup service commits once."""
        estate = Estate(**fields)
        self._db.add(estate)
        await self._db.flush()
        return estate

    async def save(self, estate: Estate) -> Estate:
        """Persist field changes without committing; the calling service commits."""
        await self._db.flush()
        await self._db.refresh(estate)
        return estate
