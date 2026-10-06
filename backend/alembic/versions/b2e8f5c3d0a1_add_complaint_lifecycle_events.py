"""Add estate-scoped complaint lifecycle evidence.

Revision ID: b2e8f5c3d0a1
Revises: a1d7e4f2b9c8
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2e8f5c3d0a1"
down_revision: Union[str, Sequence[str], None] = "a1d7e4f2b9c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("complaints", sa.Column("estate_id", sa.Integer(), nullable=True))
    op.add_column(
        "complaints",
        sa.Column("priority", sa.String(length=20), server_default="normal", nullable=False),
    )
    op.add_column("complaints", sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("complaints", sa.Column("assigned_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("complaints", sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_complaints_estate_id_estates", "complaints", "estates", ["estate_id"], ["estate_id"], ondelete="RESTRICT"
    )
    op.create_index("ix_complaints_estate_id", "complaints", ["estate_id"], unique=False)
    op.create_table(
        "complaint_events",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("complaint_id", sa.Integer(), nullable=False),
        sa.Column("estate_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=True),
        sa.Column("to_status", sa.String(length=20), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaints.complaint_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["estate_id"], ["estates.estate_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(op.f("ix_complaint_events_event_id"), "complaint_events", ["event_id"], unique=False)
    op.create_index("ix_complaint_events_complaint_id", "complaint_events", ["complaint_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_complaint_events_complaint_id", table_name="complaint_events")
    op.drop_index(op.f("ix_complaint_events_event_id"), table_name="complaint_events")
    op.drop_table("complaint_events")
    op.drop_index("ix_complaints_estate_id", table_name="complaints")
    op.drop_constraint("fk_complaints_estate_id_estates", "complaints", type_="foreignkey")
    op.drop_column("complaints", "started_at")
    op.drop_column("complaints", "assigned_at")
    op.drop_column("complaints", "reviewed_at")
    op.drop_column("complaints", "priority")
    op.drop_column("complaints", "estate_id")
