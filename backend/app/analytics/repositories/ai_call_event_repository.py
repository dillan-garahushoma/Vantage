"""Append-only, estate-scoped persistence for the AI call ledger."""
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.models.ai_call_event import AICallEvent

# The statuses that represent an attempt against the provider, and therefore
# consume an estate's daily AI budget. Rejections are auditable but free.
COUNTED_STATUSES: tuple[str, ...] = ("ok", "provider_failed")


class AICallEventRepository:
    """Records AI call metadata. There is deliberately no update or delete."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def record(
        self,
        *,
        estate_id: int,
        feature: str,
        provider: str,
        model: str,
        status: str,
        reason: str | None = None,
        latency_ms: int | None = None,
        input_chars: int | None = None,
    ) -> None:
        """Append one ledger row.

        Flushes rather than commits: the owning service commits once, so the
        row and the caller's own writes land in the same transaction.
        """
        self._db.add(
            AICallEvent(
                estate_id=estate_id,
                feature=feature,
                provider=provider,
                model=model,
                status=status,
                reason=reason,
                latency_ms=latency_ms,
                input_chars=input_chars,
            )
        )
        await self._db.flush()

    @staticmethod
    def count_statement(
        *, estate_id: int, since: datetime, statuses: Sequence[str]
    ) -> Select:
        """Build the estate-scoped count query used by the budget guard.

        Exposed as a pure function so the shape of the query (and therefore the
        tenant scoping) is testable without a database.
        """
        return (
            select(func.count())
            .select_from(AICallEvent)
            .where(
                AICallEvent.estate_id == estate_id,
                AICallEvent.created_at >= since,
                AICallEvent.status.in_(sorted(statuses)),
            )
        )

    async def count_since(
        self, *, estate_id: int, since: datetime, statuses: Sequence[str]
    ) -> int:
        """Count ledger rows for one estate at or after ``since``."""
        result = await self._db.execute(
            self.count_statement(estate_id=estate_id, since=since, statuses=statuses)
        )
        return int(result.scalar_one())
