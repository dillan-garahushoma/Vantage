"""Persistence for advisory complaint triage suggestions.

Every read is estate-scoped, so a suggestion can never be reached across the
tenant boundary. The suggestion columns are insert-only; the only mutation this
repository offers is the write-once decision, which is guarded in SQL.
"""
from sqlalchemy import Select, Update, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.community.models.complaint_ai_suggestion import ComplaintAISuggestion


class ComplaintAISuggestionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_complaint_id_in_estate(
        self, *, complaint_id: int, estate_id: int
    ) -> ComplaintAISuggestion | None:
        result = await self._db.execute(
            select(ComplaintAISuggestion).where(
                ComplaintAISuggestion.complaint_id == complaint_id,
                ComplaintAISuggestion.estate_id == estate_id,
            )
        )
        return result.scalar_one_or_none()

    async def add(
        self,
        *,
        complaint_id: int,
        estate_id: int,
        suggested_category: str,
        suggested_priority: str,
        suggested_trade: str | None,
        provider: str,
        model: str,
        prompt_version: str,
    ) -> ComplaintAISuggestion:
        """Insert the single suggestion for a complaint.

        Flushes rather than commits: the owning service commits once.
        """
        suggestion = ComplaintAISuggestion(
            complaint_id=complaint_id,
            estate_id=estate_id,
            suggested_category=suggested_category,
            suggested_priority=suggested_priority,
            suggested_trade=suggested_trade,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
        )
        self._db.add(suggestion)
        await self._db.flush()
        return suggestion

    @staticmethod
    def decision_statement(
        *,
        suggestion_id: int,
        estate_id: int,
        decision: str,
        decided_by: int,
        decided_category: str | None,
        decided_priority: str | None,
        decided_trade: str | None,
    ) -> Update:
        """Build the conditional write-once decision update.

        ``decision IS NULL`` makes the write-once rule a database guarantee
        rather than a read-then-write race: two admins deciding at the same time
        produce exactly one row update, and the loser is told to reload.
        Exposed as a pure function so the shape is testable without a database.
        """
        return (
            update(ComplaintAISuggestion)
            .where(
                ComplaintAISuggestion.suggestion_id == suggestion_id,
                ComplaintAISuggestion.estate_id == estate_id,
                ComplaintAISuggestion.decision.is_(None),
            )
            .values(
                decision=decision,
                decided_by=decided_by,
                decided_at=func.now(),
                decided_category=decided_category,
                decided_priority=decided_priority,
                decided_trade=decided_trade,
            )
        )

    async def record_decision(
        self,
        *,
        suggestion_id: int,
        estate_id: int,
        decision: str,
        decided_by: int,
        decided_category: str | None,
        decided_priority: str | None,
        decided_trade: str | None,
    ) -> bool:
        """Write the decision once. Returns False when it was already decided."""
        result = await self._db.execute(
            self.decision_statement(
                suggestion_id=suggestion_id,
                estate_id=estate_id,
                decision=decision,
                decided_by=decided_by,
                decided_category=decided_category,
                decided_priority=decided_priority,
                decided_trade=decided_trade,
            )
        )
        await self._db.flush()
        return int(result.rowcount or 0) == 1

    async def list_for_estate(
        self, *, estate_id: int, decision: str | None = None, limit: int = 100
    ) -> list[ComplaintAISuggestion]:
        """The HOA review queue: undecided first, newest first."""
        statement: Select = select(ComplaintAISuggestion).where(
            ComplaintAISuggestion.estate_id == estate_id
        )
        if decision is not None:
            statement = statement.where(ComplaintAISuggestion.decision == decision)
        statement = statement.order_by(ComplaintAISuggestion.created_at.desc()).limit(limit)
        result = await self._db.execute(statement)
        return list(result.scalars().all())
