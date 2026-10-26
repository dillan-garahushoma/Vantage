"""Add publishable unit listings and per-unit photo metadata.

Revision ID: c7e2a9b4d6f1
Revises: e8c3a1f9d5b7
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c7e2a9b4d6f1"
down_revision: Union[str, Sequence[str], None] = "e8c3a1f9d5b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("properties", sa.Column("listing_title", sa.String(length=160), nullable=True))
    op.add_column("properties", sa.Column("listing_description", sa.Text(), nullable=True))
    op.add_column("properties", sa.Column("amenities", sa.JSON(), server_default=sa.text("'[]'"), nullable=False))
    op.add_column("properties", sa.Column("is_public_listing", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("properties", sa.Column("availability_status", sa.String(length=20), server_default=sa.text("'not_available'"), nullable=False))
    op.create_index(
        "ix_properties_public_units",
        "properties",
        ["estate_id", "is_public_listing", "availability_status"],
        unique=False,
    )
    op.create_table(
        "property_photos",
        sa.Column("photo_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.unit_id", ondelete="CASCADE"), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False, unique=True),
        sa.Column("content_type", sa.String(length=32), server_default="image/jpeg", nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=False),
        sa.Column("caption", sa.String(length=140), nullable=True),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("width > 0 AND height > 0 AND bytes > 0", name="ck_property_photos_dimensions_positive"),
    )
    op.create_index("ix_property_photos_property_id_position", "property_photos", ["property_id", "position"])


def downgrade() -> None:
    op.drop_index("ix_property_photos_property_id_position", table_name="property_photos")
    op.drop_table("property_photos")
    op.drop_index("ix_properties_public_units", table_name="properties")
    op.drop_column("properties", "availability_status")
    op.drop_column("properties", "is_public_listing")
    op.drop_column("properties", "amenities")
    op.drop_column("properties", "listing_description")
    op.drop_column("properties", "listing_title")
