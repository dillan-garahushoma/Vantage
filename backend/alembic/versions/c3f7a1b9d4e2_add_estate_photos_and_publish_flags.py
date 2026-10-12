"""Add the estate publish flags and estate photos.

ONB MASTER P2. Additive and non-destructive:

1. ``estates.is_public`` (BOOLEAN NOT NULL default false) - whether the estate may
   appear in the unauthenticated public directory. Default false, so the moment
   this migration runs every existing estate is private and nothing about it
   becomes public by accident.
2. ``estates.show_living_score`` (BOOLEAN NOT NULL default false) - whether the
   public detail may expose the estate's latest stored Living Score. Separate from
   ``is_public`` on purpose: publishing a complex's photos and description is not
   the same decision as publishing its operational health.
3. ``estate_photos`` - the estate's photographs. The row is metadata only; the
   bytes live under ``UPLOAD_DIR`` as ``<public_id>.jpg`` (full) and
   ``<public_id>_thumb.jpg`` (480 px), both re-encoded from the upload, so no
   original filename, EXIF or GPS ever reaches disk. ``public_id`` is a 32-char
   random token, unique for all time: it is the only handle the public endpoint
   accepts, so a photo cannot be enumerated by counting ids.

Both new boolean columns carry a server default (``false``), which PostgreSQL 11+
applies as a fast metadata-only default, so the upgrade does not rewrite
``estates`` and is safe to run against a populated database while the application
is live. The new table starts empty and nothing existing is altered.

Downgrade: the two columns and the table are dropped, which loses only photo
metadata and the two publish flags. Nothing else references them.

Revision ID: c3f7a1b9d4e2
Revises: b1e4f7a9c2d5
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3f7a1b9d4e2"
down_revision: Union[str, Sequence[str], None] = "b1e4f7a9c2d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "estates",
        sa.Column(
            "is_public",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "estates",
        sa.Column(
            "show_living_score",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    op.create_table(
        "estate_photos",
        sa.Column("photo_id", sa.Integer(), nullable=False),
        sa.Column("estate_id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column(
            "content_type",
            sa.String(length=32),
            nullable=False,
            server_default="image/jpeg",
        ),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=False),
        sa.Column("caption", sa.String(length=140), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "width > 0 AND height > 0 AND bytes > 0",
            name="ck_estate_photos_dimensions_positive",
        ),
        sa.ForeignKeyConstraint(
            ["estate_id"],
            ["estates.estate_id"],
            name="fk_estate_photos_estate_id_estates",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["users.user_id"],
            name="fk_estate_photos_uploaded_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("photo_id"),
        sa.UniqueConstraint("public_id", name="uq_estate_photos_public_id"),
    )
    op.create_index(
        "ix_estate_photos_estate_id_position",
        "estate_photos",
        ["estate_id", "position"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_estate_photos_estate_id_position", table_name="estate_photos")
    op.drop_table("estate_photos")
    op.drop_column("estates", "show_living_score")
    op.drop_column("estates", "is_public")
