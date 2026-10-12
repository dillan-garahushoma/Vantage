"""Add the AI brief tables (BATCH AI-4).

Two purely additive tables for the estate health brief. Neither holds a prompt, a
system message, a provider response or any resident text, so an audit of either
one cannot leak what was asked or what came back.

``ai_insights`` stores one AI-written brief per snapshot:

* ``uq_ai_insights_snapshot_kind_prompt_version`` — one brief per score per kind
  per prompt version, which is what makes a re-generate return the stored brief
  and a concurrent pair of generates collapse to a single row;
* ``fk_..._snapshot_id_living_score_snapshots`` ON DELETE RESTRICT — a brief is
  evidence about a score and must not outlive it;
* ``fk_..._estate_id_estates`` ON DELETE RESTRICT — operational history does not
  vanish when an estate is removed;
* ``ck_..._kind`` / ``ck_..._data_origin`` — the closed vocabularies from
  ``app/analytics/domain/insight_vocabulary.py``, so the database refuses a kind or
  an origin the API would also refuse;
* ``ck_..._facts_object`` / ``ck_..._output_object`` — both JSONB columns must
  hold an object; a scalar or an array would be unreadable by the contract;
* ``ix_ai_insights_estate_id_created_at`` — the estate read, newest first.

``ai_insight_feedback`` stores one member's verdict per brief:

* ``uq_ai_insight_feedback_insight_id_user_id`` — one answer per member, enforced
  by the database rather than by a read-then-write check;
* ``fk_..._insight_id_ai_insights`` ON DELETE CASCADE — a verdict has no meaning
  without the brief it is about;
* ``fk_..._user_id_users`` ON DELETE SET NULL — the verdict survives the departure
  of the person who left it, anonymised;
* ``ck_..._comment_length`` — the DTO's 500-character bound, restated in SQL
  because the DTO is not the only way into the table.

Both tables are new, so every column starts NULL-free by construction and there is
no pre-flight data check to run; no existing row is read, moved or deleted.

Revision ID: d9f2a4c7e1b3
Revises: c4d8f1a7b9e3
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.analytics.domain.insight_vocabulary import (
    comment_length_check,
    data_origin_check,
    json_object_check,
    kind_check,
)

revision: str = "d9f2a4c7e1b3"
down_revision: Union[str, Sequence[str], None] = "c4d8f1a7b9e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_insights",
        sa.Column("insight_id", sa.Integer(), nullable=False),
        sa.Column("estate_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("facts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("data_origin", sa.String(length=10), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("insight_id"),
        sa.UniqueConstraint(
            "snapshot_id",
            "kind",
            "prompt_version",
            name="uq_ai_insights_snapshot_kind_prompt_version",
        ),
        sa.ForeignKeyConstraint(
            ["estate_id"],
            ["estates.estate_id"],
            name="fk_ai_insights_estate_id_estates",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["living_score_snapshots.snapshot_id"],
            name="fk_ai_insights_snapshot_id_living_score_snapshots",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(kind_check(), name="ck_ai_insights_kind"),
        sa.CheckConstraint(data_origin_check(), name="ck_ai_insights_data_origin"),
        sa.CheckConstraint(json_object_check("facts"), name="ck_ai_insights_facts_object"),
        sa.CheckConstraint(json_object_check("output"), name="ck_ai_insights_output_object"),
    )
    op.create_index(
        "ix_ai_insights_estate_id_created_at",
        "ai_insights",
        ["estate_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "ai_insight_feedback",
        sa.Column("feedback_id", sa.Integer(), nullable=False),
        sa.Column("insight_id", sa.Integer(), nullable=False),
        sa.Column("estate_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("helpful", sa.Boolean(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("feedback_id"),
        sa.UniqueConstraint(
            "insight_id",
            "user_id",
            name="uq_ai_insight_feedback_insight_id_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["insight_id"],
            ["ai_insights.insight_id"],
            name="fk_ai_insight_feedback_insight_id_ai_insights",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["estate_id"],
            ["estates.estate_id"],
            name="fk_ai_insight_feedback_estate_id_estates",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name="fk_ai_insight_feedback_user_id_users",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            comment_length_check(), name="ck_ai_insight_feedback_comment_length"
        ),
    )


def downgrade() -> None:
    op.drop_table("ai_insight_feedback")
    op.drop_index("ix_ai_insights_estate_id_created_at", table_name="ai_insights")
    op.drop_table("ai_insights")
