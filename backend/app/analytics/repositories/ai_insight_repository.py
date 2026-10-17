"""Append-only, estate-scoped persistence for stored AI briefs (BATCH AI-4).

A brief is written once. There is deliberately no update, no delete and no upsert
here: a brief a resident has read, and that a resident has rated, must keep
saying what it said.

Every read is scoped by ``estate_id``. A brief is never reachable across the
tenant boundary by accident, and the statement builders are exposed as pure
functions so the shape of each query (and therefore its scoping) is testable
without a database. Writes flush only: the owning service commits once.
"""
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.models.ai_insight import AIInsight


class AIInsightRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @staticmethod
    def for_snapshot_statement(
        *, estate_id: int, snapshot_id: int, kind: str, prompt_version: str
    ) -> Select:
        """The single brief for one snapshot, at one prompt version."""
        return (
            select(AIInsight)
            .where(
                AIInsight.estate_id == estate_id,
                AIInsight.snapshot_id == snapshot_id,
                AIInsight.kind == kind,
                AIInsight.prompt_version == prompt_version,
            )
            .order_by(AIInsight.insight_id.desc())
            .limit(1)
        )

    @staticmethod
    def by_id_statement(*, estate_id: int, insight_id: int) -> Select:
        """One brief, but only inside its own estate."""
        return select(AIInsight).where(
            AIInsight.insight_id == insight_id,
            AIInsight.estate_id == estate_id,
        )

    async def get_for_snapshot(
        self, *, estate_id: int, snapshot_id: int, kind: str, prompt_version: str
    ) -> AIInsight | None:
        """The stored brief for a snapshot, or ``None`` if it was never written."""
        result = await self._db.execute(
            self.for_snapshot_statement(
                estate_id=estate_id,
                snapshot_id=snapshot_id,
                kind=kind,
                prompt_version=prompt_version,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_in_estate(
        self, *, insight_id: int, estate_id: int
    ) -> AIInsight | None:
        """One brief by id, scoped to its estate. Another estate's is invisible."""
        result = await self._db.execute(
            self.by_id_statement(estate_id=estate_id, insight_id=insight_id)
        )
        return result.scalar_one_or_none()

    async def add(
        self,
        *,
        estate_id: int,
        snapshot_id: int,
        kind: str,
        prompt_version: str,
        provider: str,
        model: str,
        facts: dict,
        output: dict,
        data_origin: str,
    ) -> AIInsight:
        """Append one brief.

        Flushes rather than commits: the calling service commits once, so the
        brief, the caller's audit ledger row and anything else in the use case
        land in the same transaction. The unique constraint on
        ``(snapshot_id, kind, prompt_version)`` is what makes a concurrent second
        write fail rather than duplicate.
        """
        insight = AIInsight(
            estate_id=estate_id,
            snapshot_id=snapshot_id,
            kind=kind,
            prompt_version=prompt_version,
            provider=provider,
            model=model,
            facts=facts,
            output=output,
            data_origin=data_origin,
        )
        self._db.add(insight)
        await self._db.flush()
        await self._db.refresh(insight)
        return insight
