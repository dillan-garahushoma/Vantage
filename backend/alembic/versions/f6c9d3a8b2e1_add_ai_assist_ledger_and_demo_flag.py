"""Add the AI assist call ledger and the estate demo flag.

Two additive changes for BATCH AI-2, both non-destructive:

1. ``estates.is_demo`` (BOOLEAN NOT NULL DEFAULT false). The server default
   backfills every existing estate as a real estate, so no data is touched and
   no row is rewritten by hand.
2. ``ai_call_events``, the append-only ledger of AI assist calls. Metadata only:
   there is deliberately no column for a prompt, a provider response or any
   resident-written text. ``estate_id`` is the tenant boundary and is protected
   with ON DELETE RESTRICT so an estate with history cannot be deleted by
   accident.

Both statements are safe on a populated database: adding a NOT NULL column with a
server default fills existing rows, and the new table starts empty. No existing
data is read, moved or deleted, so there is no pre-flight check to fail.

Revision ID: f6c9d3a8b2e1
Revises: e5b8c2f1a4d7
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6c9d3a8b2e1"
down_revision: Union[str, Sequence[str], None] = "e5b8c2f1a4d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "estates",
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "ai_call_events",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("estate_id", sa.Integer(), nullable=False),
        sa.Column("feature", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_chars", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('ok', 'provider_failed', 'rejected_policy', 'rejected_budget')",
            name="ck_ai_call_events_status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["estate_id"],
            ["estates.estate_id"],
            name="fk_ai_call_events_estate_id_estates",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_ai_call_events_estate_id_created_at",
        "ai_call_events",
        ["estate_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ai_call_events_estate_id_created_at", table_name="ai_call_events")
    op.drop_table("ai_call_events")
    op.drop_column("estates", "is_demo")
