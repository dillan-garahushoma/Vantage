"""Persistence for estate residency requests.

Repositories flush, they never commit: the service owns the single commit for a
multi-step use case (see the architecture rules). Every read that an administrator
performs is estate-scoped by ``estate_id`` at the query, so a request id from
another estate is a 404 rather than a 403 that would confirm the row exists.
"""
from __future__ import annotations

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.models.estate_residency_request import EstateResidencyRequest


class EstateResidencyRequestRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ---- writes ----------------------------------------------------------

    async def add(self, **fields: object) -> EstateResidencyRequest:
        """Insert one request without committing; the service commits once."""
        row = EstateResidencyRequest(**fields)
        self._db.add(row)
        await self._db.flush()
        return row

    async def save(self, row: EstateResidencyRequest) -> EstateResidencyRequest:
        """Persist an in-place change without committing."""
        self._db.add(row)
        await self._db.flush()
        return row

    # ---- reads -----------------------------------------------------------

    async def get_by_id_in_estate(
        self, *, request_id: int, estate_id: int, for_update: bool = False
    ) -> EstateResidencyRequest | None:
        """Fetch one request only when it belongs to the requested estate.

        ``for_update`` takes a row lock so two administrators deciding the same
        request at once cannot both see it as pending; the loser of that race
        reads the committed status and is refused instead of overwriting it.
        """
        stmt = select(EstateResidencyRequest).where(
            EstateResidencyRequest.request_id == request_id,
            EstateResidencyRequest.estate_id == estate_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pending_for_user_and_estate(
        self, *, user_id: int, estate_id: int
    ) -> EstateResidencyRequest | None:
        """The one pending request a user may hold for an estate, if any."""
        result = await self._db.execute(
            select(EstateResidencyRequest)
            .where(
                EstateResidencyRequest.user_id == user_id,
                EstateResidencyRequest.estate_id == estate_id,
                EstateResidencyRequest.status == "pending",
            )
            .order_by(EstateResidencyRequest.request_id)
            .limit(1)
        )
        return result.scalars().first()

    def _filtered(
        self, stmt: Select, *, estate_id: int, status: str | None, search: str | None
    ) -> Select:
        stmt = stmt.where(EstateResidencyRequest.estate_id == estate_id)
        if status is not None:
            stmt = stmt.where(EstateResidencyRequest.status == status)
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(EstateResidencyRequest.applicant_name).like(term),
                    func.lower(EstateResidencyRequest.applicant_email).like(term),
                    func.lower(EstateResidencyRequest.unit_no).like(term),
                )
            )
        return stmt

    async def list_for_estate(
        self,
        *,
        estate_id: int,
        status: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[EstateResidencyRequest]:
        """One page of requests, newest first, with the id as a stable tie-break."""
        stmt = self._filtered(
            select(EstateResidencyRequest), estate_id=estate_id, status=status, search=search
        ).order_by(
            EstateResidencyRequest.created_at.desc(),
            EstateResidencyRequest.request_id.desc(),
        )
        result = await self._db.execute(stmt.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count_for_estate(
        self, *, estate_id: int, status: str | None = None, search: str | None = None
    ) -> int:
        stmt = self._filtered(
            select(func.count()).select_from(EstateResidencyRequest),
            estate_id=estate_id,
            status=status,
            search=search,
        )
        result = await self._db.execute(stmt)
        return int(result.scalar_one())

    async def count_pending_for_estate(self, *, estate_id: int) -> int:
        """The badge number: how many requests an admin still has to decide."""
        result = await self._db.execute(
            select(func.count())
            .select_from(EstateResidencyRequest)
            .where(
                EstateResidencyRequest.estate_id == estate_id,
                EstateResidencyRequest.status == "pending",
            )
        )
        return int(result.scalar_one())

    async def list_for_user(self, *, user_id: int) -> list[EstateResidencyRequest]:
        """Every request one person has submitted, across estates, newest first."""
        result = await self._db.execute(
            select(EstateResidencyRequest)
            .where(EstateResidencyRequest.user_id == user_id)
            .order_by(
                EstateResidencyRequest.created_at.desc(),
                EstateResidencyRequest.request_id.desc(),
            )
        )
        return list(result.scalars().all())
