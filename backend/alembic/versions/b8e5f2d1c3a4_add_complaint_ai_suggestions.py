"""Add the advisory AI triage suggestion table.

One purely additive table for BATCH AI-3. It stores labels only: a suggested
category, priority and trade, the provider provenance, and a write-once decision
written by an HOA admin. There is deliberately no column for a prompt, a provider
response or any complaint text, so the table cannot leak either.

Constraints come from ``app/community/domain/triage_vocabulary.py``, so the
database refuses anything outside the controlled vocabulary that the API and the
provider schema also enforce:

* ``uq_complaint_ai_suggestions_complaint_id`` — one suggestion per complaint;
* ``fk_..._complaint_id_complaints`` ON DELETE CASCADE — a suggestion cannot
  outlive its complaint, and has no meaning without it;
* ``fk_..._estate_id_estates`` ON DELETE RESTRICT — operational history does not
  vanish when an estate is removed;
* ``fk_..._decided_by_users`` ON DELETE SET NULL — the decision survives the
  departure of the admin who made it;
* ``ix_complaint_ai_suggestions_estate_id_decision`` — the HOA review queue:
  "which suggestions in this estate are still undecided?".

The table is new, so every column starts NULL-free by construction and there is
no pre-flight check to fail; no existing row is read, moved or deleted.

Revision ID: b8e5f2d1c3a4
Revises: f6c9d3a8b2e1
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.community.domain.triage_vocabulary import (
    CATEGORIES,
    DECISIONS,
    PRIORITIES,
    TRADES,
    nullable_sql_in,
    sql_in,
)


revision: str = "b8e5f2d1c3a4"
down_revision: Union[str, Sequence[str], None] = "f6c9d3a8b2e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "complaint_ai_suggestions",
        sa.Column("suggestion_id", sa.Integer(), nullable=False),
        sa.Column("complaint_id", sa.Integer(), nullable=False),
        sa.Column("estate_id", sa.Integer(), nullable=False),
        sa.Column("suggested_category", sa.String(length=32), nullable=False),
        sa.Column("suggested_priority", sa.String(length=20), nullable=False),
        sa.Column("suggested_trade", sa.String(length=32), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(length=20), nullable=True),
        sa.Column("decided_by", sa.Integer(), nullable=True),
        sa.Column("decided_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("decided_category", sa.String(length=32), nullable=True),
        sa.Column("decided_priority", sa.String(length=20), nullable=True),
        sa.Column("decided_trade", sa.String(length=32), nullable=True),
        sa.PrimaryKeyConstraint("suggestion_id"),
        sa.UniqueConstraint(
            "complaint_id", name="uq_complaint_ai_suggestions_complaint_id"
        ),
        sa.ForeignKeyConstraint(
            ["complaint_id"],
            ["complaints.complaint_id"],
            name="fk_complaint_ai_suggestions_complaint_id_complaints",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["estate_id"],
            ["estates.estate_id"],
            name="fk_complaint_ai_suggestions_estate_id_estates",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by"],
            ["users.user_id"],
            name="fk_complaint_ai_suggestions_decided_by_users",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            sql_in("suggested_category", CATEGORIES),
            name="ck_complaint_ai_suggestions_suggested_category",
        ),
        sa.CheckConstraint(
            sql_in("suggested_priority", PRIORITIES),
            name="ck_complaint_ai_suggestions_suggested_priority",
        ),
        sa.CheckConstraint(
            nullable_sql_in("suggested_trade", TRADES),
            name="ck_complaint_ai_suggestions_suggested_trade",
        ),
        sa.CheckConstraint(
            nullable_sql_in("decision", DECISIONS),
            name="ck_complaint_ai_suggestions_decision",
        ),
        sa.CheckConstraint(
            nullable_sql_in("decided_category", CATEGORIES),
            name="ck_complaint_ai_suggestions_decided_category",
        ),
        sa.CheckConstraint(
            nullable_sql_in("decided_priority", PRIORITIES),
            name="ck_complaint_ai_suggestions_decided_priority",
        ),
        sa.CheckConstraint(
            nullable_sql_in("decided_trade", TRADES),
            name="ck_complaint_ai_suggestions_decided_trade",
        ),
    )
    op.create_index(
        "ix_complaint_ai_suggestions_estate_id_decision",
        "complaint_ai_suggestions",
        ["estate_id", "decision"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_complaint_ai_suggestions_estate_id_decision",
        table_name="complaint_ai_suggestions",
    )
    op.drop_table("complaint_ai_suggestions")
