"""Add the immutable Living Score snapshot table.

One purely additive table for BATCH 7B. A row is one versioned calculation of
Living Score v1.0.0 for one estate at one ``as_of``, plus the aggregates the engine
consumed and its full reasoning, so a historical number can always be explained
without recomputing it.

Constraints come from ``app/analytics/domain/snapshot_vocabulary.py``, so the
database enforces exactly what the engine can produce:

* ``fk_living_score_snapshots_estate_id_estates`` ON DELETE RESTRICT - a score is
  operational history and does not vanish when an estate is removed;
* ``fk_living_score_snapshots_calculated_by_users`` ON DELETE SET NULL - the
  measurement survives the departure of the admin who asked for it;
* ``ck_living_score_snapshots_status`` - only the engine's two statuses;
* ``ck_living_score_snapshots_scores_bounded`` - every score is inside [0, 100],
  while NULL (insufficient data for that component) still passes;
* ``ck_living_score_snapshots_status_matches_overall`` - a scored snapshot has an
  overall score, and an insufficient-data snapshot has none;
* ``ix_living_score_snapshots_estate_id_as_of`` on (estate_id, as_of DESC) - the
  history read, newest first.

There is deliberately no ``updated_at`` and no write path beyond INSERT: a
corrected score is a new snapshot carrying its own ``engine_version``, never an
edit of an existing row. The legacy 40/30/30 per-property score is not read,
migrated or backfilled by this migration.

The table is new, so every column starts NULL-free by construction and there is no
pre-flight check to fail; no existing row is read, moved or deleted.

Revision ID: c4d8f1a7b9e3
Revises: a7c1e9d4f6b2
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.analytics.domain.snapshot_vocabulary import (
    SNAPSHOT_STATUSES,
    scores_bounded_check,
    sql_in,
    status_matches_overall_check,
)


revision: str = "c4d8f1a7b9e3"
down_revision: Union[str, Sequence[str], None] = "a7c1e9d4f6b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "living_score_snapshots",
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("estate_id", sa.Integer(), nullable=False),
        sa.Column("engine_version", sa.String(length=20), nullable=False),
        sa.Column("as_of", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("window_start", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "calculated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("calculated_by", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("overall_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("measured_weight", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("resolution_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("frequency_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("security_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("satisfaction_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("infrastructure_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("inputs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("explanation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("snapshot_id"),
        sa.ForeignKeyConstraint(
            ["estate_id"],
            ["estates.estate_id"],
            name="fk_living_score_snapshots_estate_id_estates",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["calculated_by"],
            ["users.user_id"],
            name="fk_living_score_snapshots_calculated_by_users",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            sql_in("status", SNAPSHOT_STATUSES),
            name="ck_living_score_snapshots_status",
        ),
        sa.CheckConstraint(
            scores_bounded_check(),
            name="ck_living_score_snapshots_scores_bounded",
        ),
        sa.CheckConstraint(
            status_matches_overall_check(),
            name="ck_living_score_snapshots_status_matches_overall",
        ),
    )
    op.create_index(
        "ix_living_score_snapshots_estate_id_as_of",
        "living_score_snapshots",
        ["estate_id", sa.text("as_of DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_living_score_snapshots_estate_id_as_of", table_name="living_score_snapshots")
    op.drop_table("living_score_snapshots")
