"""Restore confirmed estates to live and published status.

Revision ID: e8c3a1f9d5b7
Revises: a5c7e9f1b3d5
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e8c3a1f9d5b7"
down_revision: Union[str, Sequence[str], None] = "a5c7e9f1b3d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_BACKUP_TABLE = "migration_e8c3a1f9d5b7_estate_flags"
_NAMES = (
    "Eastbank Court",
    "Lakeside Gardens",
    "Quarry View Flats",
    "Silverleaf Reserve",
    "Willowbrook Mews",
)
_NAME_LIST = ", ".join(repr(name) for name in _NAMES)


def upgrade() -> None:
    op.create_table(
        _BACKUP_TABLE,
        sa.Column("estate_id", sa.Integer(), primary_key=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("show_living_score", sa.Boolean(), nullable=False),
    )
    op.execute(
        f"INSERT INTO {_BACKUP_TABLE} (estate_id, is_demo, is_public, show_living_score) "
        f"SELECT estate_id, is_demo, is_public, show_living_score FROM estates WHERE name IN ({_NAME_LIST})"
    )
    op.execute(
        "UPDATE estates SET is_demo = false, is_public = true, show_living_score = true "
        f"WHERE name IN ({_NAME_LIST})"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE estates AS estate SET is_demo = prior.is_demo, is_public = prior.is_public, "
        f"show_living_score = prior.show_living_score FROM {_BACKUP_TABLE} AS prior "
        "WHERE estate.estate_id = prior.estate_id"
    )
    op.drop_table(_BACKUP_TABLE)
