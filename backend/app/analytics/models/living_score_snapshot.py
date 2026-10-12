"""The immutable Living Score snapshot (BATCH 7B).

One row is one calculation of Living Score v1.0.0 for one estate at one ``as_of``.
Snapshots exist so a historical value can never move: the engine is versioned
(``engine_version``), the numbers are frozen, and the two JSONB columns carry
everything needed to explain the number later without recomputing it - the window
aggregates the engine saw (``inputs``) and the engine's full reasoning
(``explanation``: per-component scores, raw inputs, benchmarks, drivers).

Immutability is enforced by omission: there is no update path in
``LivingScoreSnapshotRepository`` and no updated_at column, because a corrected
score is a NEW snapshot, never an edit of an old one. ``estate_id`` is the tenant
boundary - the legacy NULL-estate rows of the community tables are deliberately
not part of any estate's score.
"""
from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    TIMESTAMP,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.analytics.domain.snapshot_vocabulary import (
    SNAPSHOT_STATUSES,
    scores_bounded_check,
    sql_in,
    status_matches_overall_check,
)
from app.db.base import Base


class LivingScoreSnapshot(Base):
    """One versioned, immutable Living Score calculation for one estate."""

    __tablename__ = "living_score_snapshots"

    __table_args__ = (
        CheckConstraint(
            sql_in("status", SNAPSHOT_STATUSES),
            name="ck_living_score_snapshots_status",
        ),
        CheckConstraint(
            scores_bounded_check(),
            name="ck_living_score_snapshots_scores_bounded",
        ),
        CheckConstraint(
            status_matches_overall_check(),
            name="ck_living_score_snapshots_status_matches_overall",
        ),
        # The history read: newest first, scoped to one estate.
        Index("ix_living_score_snapshots_estate_id_as_of", "estate_id", text("as_of DESC")),
    )

    snapshot_id = Column(Integer, primary_key=True, index=True)
    # Operational history outlives the estate it describes.
    estate_id = Column(
        Integer,
        ForeignKey(
            "estates.estate_id",
            ondelete="RESTRICT",
            name="fk_living_score_snapshots_estate_id_estates",
        ),
        nullable=False,
    )
    # Which formula produced this row. A new engine version writes new snapshots;
    # it never rewrites these.
    engine_version = Column(String(20), nullable=False)
    # The window is [window_start, as_of], both ends inclusive (7A decision D1).
    as_of = Column(TIMESTAMP(timezone=True), nullable=False)
    window_start = Column(TIMESTAMP(timezone=True), nullable=False)
    calculated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    # NULL for the CLI/backfill path, or after the acting admin's account is gone.
    calculated_by = Column(
        Integer,
        ForeignKey(
            "users.user_id",
            ondelete="SET NULL",
            name="fk_living_score_snapshots_calculated_by_users",
        ),
        nullable=True,
    )
    status = Column(String(20), nullable=False)
    # NULL overall means "not enough of the estate was measurable" (7A decision D3),
    # which the status/overall check keeps consistent with the status column.
    overall_score = Column(Numeric(5, 2), nullable=True)
    measured_weight = Column(Numeric(4, 2), nullable=False)
    # NULL per component = insufficient data for that component, never zero.
    resolution_score = Column(Numeric(5, 2), nullable=True)
    frequency_score = Column(Numeric(5, 2), nullable=True)
    security_score = Column(Numeric(5, 2), nullable=True)
    satisfaction_score = Column(Numeric(5, 2), nullable=True)
    infrastructure_score = Column(Numeric(5, 2), nullable=True)
    # The aggregates the engine consumed, so the number can be re-justified later.
    inputs = Column(JSONB, nullable=False)
    # The engine's per-component reasoning, benchmarks, drivers and recommendations.
    explanation = Column(JSONB, nullable=False)
