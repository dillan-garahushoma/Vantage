"""Append-only, estate-scoped persistence for Living Score snapshots.

A snapshot is a measurement, not a record to be curated: it is written once and
read forever. There is deliberately no update, no delete and no upsert here, and
no method that reads a snapshot without an ``estate_id`` - a score is never
reachable across the tenant boundary by accident.

The statement builders are exposed as pure functions so the shape of a query (and
therefore its tenant scoping) is testable without a database. Writes flush only:
the owning service commits once, so the snapshot lands in the same transaction as
the rest of the use case.
"""
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.models.living_score_snapshot import LivingScoreSnapshot


class LivingScoreSnapshotRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @staticmethod
    def latest_statement(*, estate_id: int) -> Select:
        return (
            select(LivingScoreSnapshot)
            .where(LivingScoreSnapshot.estate_id == estate_id)
            .order_by(
                LivingScoreSnapshot.as_of.desc(),
                LivingScoreSnapshot.snapshot_id.desc(),
            )
            .limit(1)
        )

    @staticmethod
    def latest_on_or_before_statement(*, estate_id: int, as_of: datetime) -> Select:
        """The newest snapshot at or before a moment - the comparison read (AI-4).

        An AI brief compares the current score against 30 and 90 days earlier. It
        asks the same question both times, so the boundary lives in one place: at
        or before, inclusive, and never past the snapshot being explained.
        """
        return (
            select(LivingScoreSnapshot)
            .where(
                LivingScoreSnapshot.estate_id == estate_id,
                LivingScoreSnapshot.as_of <= as_of,
            )
            .order_by(
                LivingScoreSnapshot.as_of.desc(),
                LivingScoreSnapshot.snapshot_id.desc(),
            )
            .limit(1)
        )

    @staticmethod
    def history_statement(*, estate_id: int, offset: int, limit: int) -> Select:
        return (
            select(LivingScoreSnapshot)
            .where(LivingScoreSnapshot.estate_id == estate_id)
            .order_by(
                LivingScoreSnapshot.as_of.desc(),
                LivingScoreSnapshot.snapshot_id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )

    @staticmethod
    def count_statement(*, estate_id: int) -> Select:
        return (
            select(func.count())
            .select_from(LivingScoreSnapshot)
            .where(LivingScoreSnapshot.estate_id == estate_id)
        )

    async def add(
        self,
        *,
        estate_id: int,
        engine_version: str,
        as_of,
        window_start,
        calculated_by: int | None,
        status: str,
        overall_score,
        measured_weight,
        resolution_score,
        frequency_score,
        security_score,
        satisfaction_score,
        infrastructure_score,
        inputs: dict,
        explanation: dict,
    ) -> LivingScoreSnapshot:
        """Append one immutable snapshot.

        Flushes rather than commits: the calling service commits once, so the row
        and the rest of the use case land in the same transaction.
        """
        snapshot = LivingScoreSnapshot(
            estate_id=estate_id,
            engine_version=engine_version,
            as_of=as_of,
            window_start=window_start,
            calculated_by=calculated_by,
            status=status,
            overall_score=overall_score,
            measured_weight=measured_weight,
            resolution_score=resolution_score,
            frequency_score=frequency_score,
            security_score=security_score,
            satisfaction_score=satisfaction_score,
            infrastructure_score=infrastructure_score,
            inputs=inputs,
            explanation=explanation,
        )
        self._db.add(snapshot)
        await self._db.flush()
        await self._db.refresh(snapshot)
        return snapshot

    async def latest_for_estate(self, *, estate_id: int) -> LivingScoreSnapshot | None:
        """The most recent calculation for one estate, or None if never scored."""
        result = await self._db.execute(self.latest_statement(estate_id=estate_id))
        return result.scalar_one_or_none()

    async def latest_on_or_before(
        self, *, estate_id: int, as_of: datetime
    ) -> LivingScoreSnapshot | None:
        """The newest snapshot at or before ``as_of``, or None if there is none."""
        result = await self._db.execute(
            self.latest_on_or_before_statement(estate_id=estate_id, as_of=as_of)
        )
        return result.scalar_one_or_none()

    async def history(
        self, *, estate_id: int, offset: int, limit: int
    ) -> list[LivingScoreSnapshot]:
        """One page of an estate's snapshots, newest first."""
        result = await self._db.execute(
            self.history_statement(estate_id=estate_id, offset=offset, limit=limit)
        )
        return list(result.scalars().all())

    async def count(self, *, estate_id: int) -> int:
        result = await self._db.execute(self.count_statement(estate_id=estate_id))
        return int(result.scalar_one())
