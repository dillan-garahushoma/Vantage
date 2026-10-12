"""Scope announcements to the estate tenant boundary.

The Announcement ORM model and AnnouncementService have always required
``announcements.estate_id``, but no migration ever added the column, so
announcements could not be created or listed on a migrated database.

The column is added nullable, matching the other estate-scoped tables: rows that
predate estate tenancy keep a NULL estate, and the estate-scoped repository
queries simply never return them.

Revision ID: e5b8c2f1a4d7
Revises: d4a7e1c9b3f2
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5b8c2f1a4d7"
down_revision: Union[str, Sequence[str], None] = "d4a7e1c9b3f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("announcements", sa.Column("estate_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_announcements_estate_id_estates",
        "announcements",
        "estates",
        ["estate_id"],
        ["estate_id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_announcements_estate_id", "announcements", ["estate_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_announcements_estate_id", table_name="announcements")
    op.drop_constraint("fk_announcements_estate_id_estates", "announcements", type_="foreignkey")
    op.drop_column("announcements", "estate_id")
