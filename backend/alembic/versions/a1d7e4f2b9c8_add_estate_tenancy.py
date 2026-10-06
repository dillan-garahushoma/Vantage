"""Add explicit estate tenancy and memberships without rewriting legacy properties.

Revision ID: a1d7e4f2b9c8
Revises: 103dd39ca30e
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1d7e4f2b9c8"
down_revision: Union[str, Sequence[str], None] = "103dd39ca30e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "estates",
        sa.Column("estate_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("suburb", sa.String(length=120), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("province", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("estate_id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_estates_estate_id"), "estates", ["estate_id"], unique=False)

    # Existing property rows have no trustworthy estate source. Keep this nullable;
    # the deterministic seed and a future controlled migration assign new data.
    op.add_column("properties", sa.Column("estate_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_properties_estate_id_estates",
        "properties",
        "estates",
        ["estate_id"],
        ["estate_id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_properties_estate_id", "properties", ["estate_id"], unique=False)

    op.create_table(
        "estate_memberships",
        sa.Column("membership_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("estate_id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=True),
        sa.Column("membership_role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["estate_id"], ["estates.estate_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.unit_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("membership_id"),
        sa.UniqueConstraint("user_id", "estate_id", "property_id", name="uq_membership_scope"),
    )
    op.create_index(op.f("ix_estate_memberships_membership_id"), "estate_memberships", ["membership_id"], unique=False)
    op.create_index("ix_estate_memberships_user_estate", "estate_memberships", ["user_id", "estate_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_estate_memberships_user_estate", table_name="estate_memberships")
    op.drop_index(op.f("ix_estate_memberships_membership_id"), table_name="estate_memberships")
    op.drop_table("estate_memberships")
    op.drop_index("ix_properties_estate_id", table_name="properties")
    op.drop_constraint("fk_properties_estate_id_estates", "properties", type_="foreignkey")
    op.drop_column("properties", "estate_id")
    op.drop_index(op.f("ix_estates_estate_id"), table_name="estates")
    op.drop_table("estates")
