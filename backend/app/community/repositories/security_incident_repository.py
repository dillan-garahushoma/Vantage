"""Estate-scoped persistence for security incidents.

Every method except ``create`` takes an ``estate_id`` and filters on it, and
there is deliberately no ``delete``: an incident is operational history, and the
Living Score reads it after the fact. There is no unscoped getter either, so an
estate-scoped route cannot reach a row through this repository by accident.
"""
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.community.models.security_incident import SecurityIncident


class SecurityIncidentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @staticmethod
    def _apply_filters(
        stmt: Select,
        *,
        estate_id: int,
        status: str | None = None,
        severity: str | None = None,
        category: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> Select:
        stmt = stmt.where(SecurityIncident.estate_id == estate_id)
        if status is not None:
            stmt = stmt.where(SecurityIncident.status == status)
        if severity is not None:
            stmt = stmt.where(SecurityIncident.severity == severity)
        if category is not None:
            stmt = stmt.where(SecurityIncident.category == category)
        # Start inclusive, end exclusive, so adjacent windows tile without
        # double-counting an incident recorded exactly on a boundary.
        if occurred_from is not None:
            stmt = stmt.where(SecurityIncident.occurred_at >= occurred_from)
        if occurred_to is not None:
            stmt = stmt.where(SecurityIncident.occurred_at < occurred_to)
        return stmt

    async def create(
        self,
        *,
        estate_id: int,
        property_id: int | None,
        category: str,
        severity: str,
        status: str,
        occurred_at: datetime,
        created_by: int | None,
    ) -> SecurityIncident:
        incident = SecurityIncident(
            estate_id=estate_id,
            property_id=property_id,
            category=category,
            severity=severity,
            status=status,
            occurred_at=occurred_at,
            created_by=created_by,
        )
        self._db.add(incident)
        await self._db.commit()
        await self._db.refresh(incident)
        return incident

    async def get_by_id_in_estate(
        self, *, incident_id: int, estate_id: int
    ) -> SecurityIncident | None:
        result = await self._db.execute(
            select(SecurityIncident).where(
                SecurityIncident.incident_id == incident_id,
                SecurityIncident.estate_id == estate_id,
            )
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        *,
        offset: int,
        limit: int,
        estate_id: int,
        status: str | None = None,
        severity: str | None = None,
        category: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> list[SecurityIncident]:
        stmt = select(SecurityIncident).order_by(
            SecurityIncident.occurred_at.desc(),
            SecurityIncident.incident_id.desc(),
        )
        stmt = self._apply_filters(
            stmt,
            estate_id=estate_id,
            status=status,
            severity=severity,
            category=category,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
        )
        result = await self._db.execute(stmt.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count(
        self,
        *,
        estate_id: int,
        status: str | None = None,
        severity: str | None = None,
        category: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(SecurityIncident)
        stmt = self._apply_filters(
            stmt,
            estate_id=estate_id,
            status=status,
            severity=severity,
            category=category,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
        )
        result = await self._db.execute(stmt)
        return int(result.scalar_one())

    async def count_in_window(self, *, estate_id: int, start: datetime, end: datetime) -> int:
        """Incidents in one estate with ``start <= occurred_at < end``.

        The Living Score security input. Deliberately status-agnostic: an
        incident happened whether or not it has been resolved, and the window is
        what the score cares about.
        """
        stmt = (
            select(func.count())
            .select_from(SecurityIncident)
            .where(
                SecurityIncident.estate_id == estate_id,
                SecurityIncident.occurred_at >= start,
                SecurityIncident.occurred_at < end,
            )
        )
        result = await self._db.execute(stmt)
        return int(result.scalar_one())

    async def save(self, incident: SecurityIncident) -> SecurityIncident:
        await self._db.commit()
        await self._db.refresh(incident)
        return incident
