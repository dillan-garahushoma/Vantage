from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    TIMESTAMP,
)
from sqlalchemy.sql import func

from app.db.base import Base


class AICallEvent(Base):
    """Append-only ledger of AI assist calls, one row per estate-scoped attempt.

    Metadata only. This table must never hold a prompt, a provider response or
    any resident-written text, so every column is a scalar code or a count.
    ``estate_id`` is the tenant boundary and every read is scoped by it.
    """

    __tablename__ = "ai_call_events"

    event_id = Column(Integer, primary_key=True)
    estate_id = Column(
        Integer,
        ForeignKey(
            "estates.estate_id",
            ondelete="RESTRICT",
            name="fk_ai_call_events_estate_id_estates",
        ),
        nullable=False,
    )
    feature = Column(String(32), nullable=False)
    provider = Column(String(32), nullable=False)
    model = Column(String(120), nullable=False)
    status = Column(String(32), nullable=False)
    reason = Column(String(32), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    input_chars = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('ok', 'provider_failed', 'rejected_policy', 'rejected_budget')",
            name="ck_ai_call_events_status_allowed",
        ),
        Index("ix_ai_call_events_estate_id_created_at", "estate_id", "created_at"),
    )
