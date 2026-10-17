from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    TIMESTAMP,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.community.domain.triage_vocabulary import (
    CATEGORIES,
    DECISIONS,
    PRIORITIES,
    TRADES,
    nullable_sql_in,
    sql_in,
)
from app.db.base import Base


class ComplaintAISuggestion(Base):
    """One advisory triage suggestion per complaint, plus a write-once decision.

    The suggestion columns are written once by the AI triage service and are
    never updated. The ``decided_*`` columns start NULL and are written exactly
    once when an HOA admin accepts, overrides or dismisses the suggestion; after
    that the row is frozen. Nothing here is load-bearing: with AI off the feature
    simply has no suggestion, and a complaint is unaffected either way.

    Labels only. There is deliberately no column for a prompt, a provider
    response or any complaint text, so the stored row cannot leak either.
    ``estate_id`` is the tenant boundary and is never taken from the client.
    """

    __tablename__ = "complaint_ai_suggestions"
    __table_args__ = (
        UniqueConstraint(
            "complaint_id", name="uq_complaint_ai_suggestions_complaint_id"
        ),
        CheckConstraint(
            sql_in("suggested_category", CATEGORIES),
            name="ck_complaint_ai_suggestions_suggested_category",
        ),
        CheckConstraint(
            sql_in("suggested_priority", PRIORITIES),
            name="ck_complaint_ai_suggestions_suggested_priority",
        ),
        CheckConstraint(
            nullable_sql_in("suggested_trade", TRADES),
            name="ck_complaint_ai_suggestions_suggested_trade",
        ),
        CheckConstraint(
            nullable_sql_in("decision", DECISIONS),
            name="ck_complaint_ai_suggestions_decision",
        ),
        CheckConstraint(
            nullable_sql_in("decided_category", CATEGORIES),
            name="ck_complaint_ai_suggestions_decided_category",
        ),
        CheckConstraint(
            nullable_sql_in("decided_priority", PRIORITIES),
            name="ck_complaint_ai_suggestions_decided_priority",
        ),
        CheckConstraint(
            nullable_sql_in("decided_trade", TRADES),
            name="ck_complaint_ai_suggestions_decided_trade",
        ),
        Index(
            "ix_complaint_ai_suggestions_estate_id_decision", "estate_id", "decision"
        ),
    )

    suggestion_id = Column(Integer, primary_key=True)
    complaint_id = Column(
        Integer,
        ForeignKey(
            "complaints.complaint_id",
            ondelete="CASCADE",
            name="fk_complaint_ai_suggestions_complaint_id_complaints",
        ),
        nullable=False,
    )
    estate_id = Column(
        Integer,
        ForeignKey(
            "estates.estate_id",
            ondelete="RESTRICT",
            name="fk_complaint_ai_suggestions_estate_id_estates",
        ),
        nullable=False,
    )
    suggested_category = Column(String(32), nullable=False)
    suggested_priority = Column(String(20), nullable=False)
    suggested_trade = Column(String(32), nullable=True)
    provider = Column(String(32), nullable=False)
    model = Column(String(120), nullable=False)
    prompt_version = Column(String(32), nullable=False)
    # Existing suggestions from the former demonstration setup are preserved for
    # audit, but never shown as a live AI result and may be replaced only by an
    # administrator's explicit request.
    is_seeded = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Write-once decision. Never set by the AI layer.
    decision = Column(String(20), nullable=True)
    decided_by = Column(
        Integer,
        ForeignKey(
            "users.user_id",
            ondelete="SET NULL",
            name="fk_complaint_ai_suggestions_decided_by_users",
        ),
        nullable=True,
    )
    decided_at = Column(TIMESTAMP(timezone=True), nullable=True)
    decided_category = Column(String(32), nullable=True)
    decided_priority = Column(String(20), nullable=True)
    decided_trade = Column(String(32), nullable=True)
