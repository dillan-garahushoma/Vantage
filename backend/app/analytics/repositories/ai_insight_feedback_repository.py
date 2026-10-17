"""Append-only persistence for brief feedback (BATCH AI-4).

Feedback is a person's opinion, not a field to edit: there is no update and no
delete here. Changing your mind means a new brief, not a rewritten verdict, and
the unique constraint on ``(insight_id, user_id)`` keeps it one answer per member.

The read is scoped by insight *and* user rather than by estate, because it is only
ever called after the brief itself has been resolved inside the caller's estate:
the estate check happens once, on the brief, and is not re-invented per query.

The comment is stored locally and never leaves the database.
"""
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.models.ai_insight_feedback import AIInsightFeedback


class AIInsightFeedbackRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @staticmethod
    def for_insight_and_user_statement(*, insight_id: int, user_id: int) -> Select:
        """One member's verdict on one brief, if they have left one."""
        return (
            select(AIInsightFeedback)
            .where(
                AIInsightFeedback.insight_id == insight_id,
                AIInsightFeedback.user_id == user_id,
            )
            .order_by(AIInsightFeedback.feedback_id.desc())
            .limit(1)
        )

    async def get_by_insight_and_user(
        self, *, insight_id: int, user_id: int
    ) -> AIInsightFeedback | None:
        result = await self._db.execute(
            self.for_insight_and_user_statement(insight_id=insight_id, user_id=user_id)
        )
        return result.scalar_one_or_none()

    async def add(
        self,
        *,
        insight_id: int,
        estate_id: int,
        user_id: int | None,
        helpful: bool,
        comment: str | None,
    ) -> AIInsightFeedback:
        """Append one verdict.

        Flushes rather than commits: the owning service commits once. A repeat
        from the same member fails on the unique constraint, which the service
        turns into a conflict rather than a duplicate row.
        """
        feedback = AIInsightFeedback(
            insight_id=insight_id,
            estate_id=estate_id,
            user_id=user_id,
            helpful=helpful,
            comment=comment,
        )
        self._db.add(feedback)
        await self._db.flush()
        await self._db.refresh(feedback)
        return feedback
