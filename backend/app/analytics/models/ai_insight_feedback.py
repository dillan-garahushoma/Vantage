"""Estate feedback on a stored AI brief (BATCH AI-4).

A brief that nobody can rate is a brief nobody can improve. One row per member
per brief, written once: the unique constraint makes "already answered" a
database fact rather than a read-then-write race.

The comment is a resident's own words, so it is stored **locally only**. It is
never sent to a provider, never included in a prompt, and it cannot change a
score or a brief.
"""
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    TIMESTAMP,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.analytics.domain.insight_vocabulary import comment_length_check
from app.db.base import Base


class AIInsightFeedback(Base):
    """One estate member's verdict on one stored brief.

    ``user_id`` is ON DELETE SET NULL so the verdict survives the departure of the
    person who left it, anonymised. ``comment`` is bounded in the DTO and again by
    a check constraint, because the DTO is not the only way into the table.
    """

    __tablename__ = "ai_insight_feedback"

    __table_args__ = (
        UniqueConstraint(
            "insight_id", "user_id", name="uq_ai_insight_feedback_insight_id_user_id"
        ),
        CheckConstraint(
            comment_length_check(), name="ck_ai_insight_feedback_comment_length"
        ),
    )

    feedback_id = Column(Integer, primary_key=True)
    # CASCADE: a verdict has no meaning without the brief it is about.
    insight_id = Column(
        Integer,
        ForeignKey(
            "ai_insights.insight_id",
            ondelete="CASCADE",
            name="fk_ai_insight_feedback_insight_id_ai_insights",
        ),
        nullable=False,
    )
    estate_id = Column(
        Integer,
        ForeignKey(
            "estates.estate_id",
            ondelete="RESTRICT",
            name="fk_ai_insight_feedback_estate_id_estates",
        ),
        nullable=False,
    )
    user_id = Column(
        Integer,
        ForeignKey(
            "users.user_id",
            ondelete="SET NULL",
            name="fk_ai_insight_feedback_user_id_users",
        ),
        nullable=True,
    )
    helpful = Column(Boolean, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
