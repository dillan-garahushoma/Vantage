"""Add HOA-reviewed provider applications and secure account setup invitations.

Revision ID: c5a7d9e1f3b2
Revises: e2f4c8b1a9d3
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c5a7d9e1f3b2"
down_revision: Union[str, Sequence[str], None] = "e2f4c8b1a9d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "provider_applications",
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("estate_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("trade", sa.String(length=50), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_provider_applications_status",
        ),
        sa.CheckConstraint(
            "status = 'pending' OR reviewed_at IS NOT NULL",
            name="ck_provider_applications_reviewed_at_present",
        ),
        sa.ForeignKeyConstraint(
            ["estate_id"],
            ["estates.estate_id"],
            name="fk_provider_applications_estate_id_estates",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.user_id"],
            name="fk_provider_applications_reviewed_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("application_id"),
    )
    op.create_index(
        "uq_provider_applications_pending_estate_email",
        "provider_applications",
        ["estate_id", "email"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_provider_applications_estate_status_created",
        "provider_applications",
        ["estate_id", "status", "created_at"],
    )

    op.create_table(
        "provider_invitations",
        sa.Column("invitation_id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("estate_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column("trade", sa.String(length=50), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["provider_applications.application_id"],
            name="fk_provider_invitations_application_id_provider_applications",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.user_id"],
            name="fk_provider_invitations_created_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["estate_id"],
            ["estates.estate_id"],
            name="fk_provider_invitations_estate_id_estates",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("invitation_id"),
    )
    op.create_index(
        "uq_provider_invitations_active_estate_email",
        "provider_invitations",
        ["estate_id", "email"],
        unique=True,
        postgresql_where=sa.text("accepted_at IS NULL AND revoked_at IS NULL"),
    )
    op.create_index(
        "ix_provider_invitations_token_digest",
        "provider_invitations",
        ["token_digest"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_provider_invitations_token_digest", table_name="provider_invitations")
    op.drop_index(
        "uq_provider_invitations_active_estate_email", table_name="provider_invitations"
    )
    op.drop_table("provider_invitations")
    op.drop_index(
        "ix_provider_applications_estate_status_created",
        table_name="provider_applications",
    )
    op.drop_index(
        "uq_provider_applications_pending_estate_email",
        table_name="provider_applications",
    )
    op.drop_table("provider_applications")
