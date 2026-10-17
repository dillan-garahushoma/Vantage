"""Aggregate the window inputs the Living Score engine consumes (BATCH 7B).

This is the only place that reads estate operations for scoring, and it reads
**aggregates, never rows**: every statement selects a count or an average, so a
snapshot costs a fixed seven statements no matter how large the estate is (there is
no ORM hydration here and therefore no N+1).

Two rules, applied to every query:

* **Estate scoping.** Each aggregate filters ``estate_id == <estate>``. The legacy
  community rows with a NULL ``estate_id`` are therefore excluded by construction -
  they belong to no estate and must never be attributed to one.
* **One window.** The bounds come from the engine's ``window_bounds(as_of)`` (7A
  decision D1: ``[as_of - 90 days, as_of]``, both ends inclusive), never re-derived
  here, so the SQL and the engine cannot drift apart.

The engine stays ignorant of all of this: it receives an ``EstateScoreInputs``.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import Select, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.engine import EstateScoreInputs, WINDOW_DAYS, window_bounds
from app.common.datetime_utils import ensure_utc
from app.common.enums import ComplaintStatus
from app.community.models.complaint import Complaint
from app.community.models.maintenance_work_order import MaintenanceworkOrder
from app.community.repositories.security_incident_repository import (
    SecurityIncidentRepository,
)
from app.core.exceptions import NotFoundException
from app.property.models.estate import Estate
from app.property.models.property import Property
from app.providers.models.service_provider import ServiceProvider

#: A complaint counts as resolved once it reaches any of these states. `rated` and
#: the legacy `closed` are both terminal resolutions, not open work.
RESOLVED_COMPLAINT_STATUSES: tuple[str, ...] = (
    ComplaintStatus.closed.value,
    ComplaintStatus.rated.value,
    ComplaintStatus.resolved.value,
)

_COMPLETED = "completed"
_SECONDS_PER_DAY = Decimal("86400")


class LivingScoreInputsRepository:
    def __init__(
        self,
        db: AsyncSession,
        *,
        incidents: SecurityIncidentRepository | None = None,
    ) -> None:
        self._db = db
        # 6B owns the incident table; reuse its window counter rather than
        # duplicating the query here.
        self._incidents = incidents if incidents is not None else SecurityIncidentRepository(db)

    # ------------------------------------------------------------------ shape #
    @staticmethod
    def unit_count_statement(*, estate_id: int) -> Select:
        """How many units the estate has (the frequency denominator)."""
        return (
            select(func.count())
            .select_from(Property)
            .where(Property.estate_id == estate_id)
        )

    @staticmethod
    def complaints_created_statement(*, estate_id: int, start: datetime, end: datetime) -> Select:
        """Complaints raised in the window."""
        return (
            select(func.count())
            .select_from(Complaint)
            .where(
                Complaint.estate_id == estate_id,
                Complaint.created_at >= start,
                Complaint.created_at <= end,
            )
        )

    @staticmethod
    def resolution_statement(*, estate_id: int, start: datetime, end: datetime) -> Select:
        """Resolved complaints in the window: the count and the average resolution days.

        Measured in the database as elapsed seconds, converted to days in Python so
        the engine receives an exact ``Decimal``.
        """
        return (
            select(
                func.count(),
                func.avg(func.extract("epoch", Complaint.resolved_at - Complaint.created_at)),
            )
            .select_from(Complaint)
            .where(
                Complaint.estate_id == estate_id,
                Complaint.status.in_(RESOLVED_COMPLAINT_STATUSES),
                Complaint.resolved_at.is_not(None),
                Complaint.resolved_at >= start,
                Complaint.resolved_at <= end,
            )
        )

    @staticmethod
    def work_orders_statement(*, estate_id: int, start: datetime, end: datetime) -> Select:
        """Work orders assigned in the window: how many, and how many completed."""
        return (
            select(
                func.count(),
                func.count(
                    case((MaintenanceworkOrder.status == _COMPLETED, MaintenanceworkOrder.work_order_id))
                ),
            )
            .select_from(MaintenanceworkOrder)
            .where(
                MaintenanceworkOrder.estate_id == estate_id,
                MaintenanceworkOrder.assigned_at >= start,
                MaintenanceworkOrder.assigned_at <= end,
            )
        )

    @staticmethod
    def ratings_statement(*, estate_id: int, start: datetime, end: datetime) -> Select:
        """Resident ratings on work orders completed in the window."""
        return (
            select(
                func.count(MaintenanceworkOrder.resident_rating),
                func.avg(MaintenanceworkOrder.resident_rating),
            )
            .select_from(MaintenanceworkOrder)
            .where(
                MaintenanceworkOrder.estate_id == estate_id,
                MaintenanceworkOrder.status == _COMPLETED,
                MaintenanceworkOrder.resident_rating.is_not(None),
                MaintenanceworkOrder.resolved_at >= start,
                MaintenanceworkOrder.resolved_at <= end,
            )
        )

    @staticmethod
    def provider_ratings_statement(*, estate_id: int, start: datetime, end: datetime) -> Select:
        """Provider ratings for the distinct providers used in the window.

        One row per provider, not per work order: a provider with five window jobs
        still counts once, so the average is not weighted by repeat business.
        """
        windowed_providers = (
            select(MaintenanceworkOrder.provider_id)
            .where(
                MaintenanceworkOrder.estate_id == estate_id,
                MaintenanceworkOrder.assigned_at >= start,
                MaintenanceworkOrder.assigned_at <= end,
            )
            .distinct()
            .subquery()
        )
        return (
            select(
                func.count(),
                func.avg(ServiceProvider.avg_rating),
            )
            .select_from(
                windowed_providers.join(
                    ServiceProvider,
                    ServiceProvider.provider_id == windowed_providers.c.provider_id,
                )
            )
            .where(ServiceProvider.avg_rating.is_not(None))
        )

    @staticmethod
    def estate_created_at_statement(*, estate_id: int) -> Select:
        """When the estate began operating, for the coverage calculation."""
        return select(Estate.created_at).where(Estate.estate_id == estate_id)

    # -------------------------------------------------------------- execution #
    async def unit_count(self, *, estate_id: int) -> int:
        return await self._scalar(self.unit_count_statement(estate_id=estate_id))

    async def gather(self, *, estate_id: int, as_of: datetime) -> EstateScoreInputs:
        """Aggregate one estate's window into the engine's inputs.

        Seven statements, one pass, in a fixed order. The averages are ``Decimal``
        and absent data is ``None`` - never a zero that would read as a real
        measurement.
        """
        start, end = window_bounds(as_of)

        created_at = await self._created_at(estate_id=estate_id)
        if created_at is None:
            raise NotFoundException(f"Estate with id {estate_id} was not found.")

        unit_count = await self._scalar(self.unit_count_statement(estate_id=estate_id))
        complaints_created = await self._scalar(
            self.complaints_created_statement(estate_id=estate_id, start=start, end=end)
        )
        resolved_complaints, avg_resolution_seconds = await self._row(
            self.resolution_statement(estate_id=estate_id, start=start, end=end)
        )
        work_orders_in_window, work_orders_completed = await self._counts(
            self.work_orders_statement(estate_id=estate_id, start=start, end=end)
        )
        rated_count, avg_rating = await self._row(
            self.ratings_statement(estate_id=estate_id, start=start, end=end)
        )
        provider_rating_count, avg_provider_rating = await self._row(
            self.provider_ratings_statement(estate_id=estate_id, start=start, end=end)
        )

        # 6B's counter is half-open (`start <= occurred_at < end`) while the
        # engine's window is inclusive at both ends (decision D1), so ask for one
        # microsecond past the boundary - the smallest step the column can store.
        incidents = await self._incidents.count_in_window(
            estate_id=estate_id,
            start=start,
            end=end + timedelta(microseconds=1),
        )

        return EstateScoreInputs(
            as_of=as_of,
            coverage_days=_coverage_days(created_at, as_of),
            unit_count=unit_count,
            complaints_created=complaints_created,
            resolved_complaints=resolved_complaints,
            avg_resolution_days=(
                None
                if avg_resolution_seconds is None
                else avg_resolution_seconds / _SECONDS_PER_DAY
            ),
            work_orders_in_window=work_orders_in_window,
            work_orders_completed=work_orders_completed,
            rated_count=rated_count,
            avg_rating=avg_rating,
            provider_rating_count=provider_rating_count,
            avg_provider_rating=avg_provider_rating,
            incidents=incidents,
        )

    # ---------------------------------------------------------------- helpers #
    async def _created_at(self, *, estate_id: int) -> datetime | None:
        result = await self._db.execute(self.estate_created_at_statement(estate_id=estate_id))
        return result.scalar_one_or_none()

    async def _scalar(self, statement: Select) -> int:
        result = await self._db.execute(statement)
        return int(result.scalar_one() or 0)

    async def _row(self, statement: Select) -> tuple[int, Decimal | None]:
        """A count paired with an average: the second value stays exact or absent."""
        result = await self._db.execute(statement)
        row = result.one()
        return int(row[0] or 0), _as_decimal(row[1])

    async def _counts(self, statement: Select) -> tuple[int, int]:
        """Two counts. Kept separate from ``_row`` so a count stays an int and is
        never coerced into a Decimal by the average path."""
        result = await self._db.execute(statement)
        row = result.one()
        return int(row[0] or 0), int(row[1] or 0)


def _coverage_days(created_at: datetime, as_of: datetime) -> int:
    """Whole days the estate has been operating, clamped to the 90-day window.

    Clamped at both ends: a brand-new estate has no history to judge (0), and an
    estate older than the window is judged on the window, not on its age. The
    engine's measurability rules (7A decision D2) read this, so the clamp is what
    stops a new estate from looking flawless.
    """
    created = ensure_utc(created_at)
    if created is None:
        return 0
    return max(0, min(WINDOW_DAYS, (as_of - created).days))


def _as_decimal(value: object) -> Decimal | None:
    """Numeric database values arrive as Decimal, int or None; never float."""
    if value is None:
        return None
    return value if isinstance(value, Decimal) else Decimal(str(value))
