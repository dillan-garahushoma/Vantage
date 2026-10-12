"""Persistence for the append-only membership event log.

There is deliberately no update and no delete method on this repository: an event
records something that happened, so it is never rewritten. Rows are only ever
inserted and read.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.models.estate_membership_event import EstateMembershipEvent


class EstateMembershipEventRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def record(self, **fields: object) -> EstateMembershipEvent:
        """Append one event without committing; the service commits once."""
        event = EstateMembershipEvent(**fields)
        self._db.add(event)
        await self._db.flush()
        return event

    async def list_for_estate(self, *, estate_id: int) -> list[EstateMembershipEvent]:
        """Every event for an estate, oldest first."""
        result = await self._db.execute(
            select(EstateMembershipEvent)
            .where(EstateMembershipEvent.estate_id == estate_id)
            .order_by(EstateMembershipEvent.event_id)
        )
        return list(result.scalars().all())
