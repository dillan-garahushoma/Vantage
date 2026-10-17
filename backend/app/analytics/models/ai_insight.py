"""A stored, AI-written estate health brief (BATCH AI-4).

One row is one brief about one snapshot. It is written once and read forever:
``AIInsightRepository`` has no update and no delete, because a brief a resident
has already read must not change under them, and the human feedback attached to
it is about *that* text.

`facts` is stored beside `output` on purpose. It is what the provider was shown,
so an audit can answer "did the model invent that number?" without a second
migration or a recomputation, and it is the material the grounding validator ran
against.
"""
from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    TIMESTAMP,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.analytics.domain.insight_vocabulary import (
    data_origin_check,
    json_object_check,
    kind_check,
)
from app.db.base import Base


class AIInsight(Base):
    """One AI-written brief for one snapshot, with the facts it was built from.

    The tenant boundary is ``estate_id`` and every read is scoped by it. There is
    deliberately no column for a prompt, a system message or a raw provider
    response: the ledger's rule (ADR-004) holds here too, so an audit of this
    table cannot leak a prompt or a provider payload.
    """

    __tablename__ = "ai_insights"

    __table_args__ = (
        # One brief per snapshot per kind per prompt version: a re-generate
        # returns the stored brief instead of paying for a second one, and a
        # concurrent pair of generates collapses to a single row.
        UniqueConstraint(
            "snapshot_id",
            "kind",
            "prompt_version",
            name="uq_ai_insights_snapshot_kind_prompt_version",
        ),
        CheckConstraint(kind_check(), name="ck_ai_insights_kind"),
        CheckConstraint(data_origin_check(), name="ck_ai_insights_data_origin"),
        CheckConstraint(json_object_check("facts"), name="ck_ai_insights_facts_object"),
        CheckConstraint(json_object_check("output"), name="ck_ai_insights_output_object"),
        # The estate read: "this estate's briefs, newest first".
        Index("ix_ai_insights_estate_id_created_at", "estate_id", "created_at"),
    )

    insight_id = Column(Integer, primary_key=True)
    estate_id = Column(
        Integer,
        ForeignKey(
            "estates.estate_id",
            ondelete="RESTRICT",
            name="fk_ai_insights_estate_id_estates",
        ),
        nullable=False,
    )
    # RESTRICT: an AI brief is evidence about a score and must not outlive it.
    snapshot_id = Column(
        Integer,
        ForeignKey(
            "living_score_snapshots.snapshot_id",
            ondelete="RESTRICT",
            name="fk_ai_insights_snapshot_id_living_score_snapshots",
        ),
        nullable=False,
    )
    kind = Column(String(30), nullable=False)
    prompt_version = Column(String(32), nullable=False)
    provider = Column(String(32), nullable=False)
    model = Column(String(120), nullable=False)
    #: The numbers the provider was given, exactly as it saw them.
    facts = Column(JSONB, nullable=False)
    #: The validated, grounded brief.
    output = Column(JSONB, nullable=False)
    #: 'demo' or 'live', copied from estates.is_demo when the brief was created.
    data_origin = Column(String(10), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
