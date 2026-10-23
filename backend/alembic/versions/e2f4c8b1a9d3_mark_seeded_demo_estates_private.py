"""Prevent the known fictional seed estates from presenting as live estates.

Only the five deterministic names emitted by ``seed_demo`` are touched. Their
previous flags are retained in a migration-local table so a downgrade restores
exactly the classifications that existed before this correction.

Revision ID: e2f4c8b1a9d3
Revises: d14a5b9e7f23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e2f4c8b1a9d3"
down_revision: Union[str, Sequence[str], None] = "d14a5b9e7f23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "migration_e2f4c8b1a9d3_seed_estate_flags"
_NAMES = (
    "Silverleaf Reserve",
    "Willowbrook Mews",
    "Lakeside Gardens",
    "Eastbank Court",
    "Quarry View Flats",
)
_NAME_LIST = ", ".join(repr(name) for name in _NAMES)


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("estate_id", sa.Integer(), primary_key=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("show_living_score", sa.Boolean(), nullable=False),
    )
    op.execute(
        f"INSERT INTO {_TABLE} (estate_id, is_demo, is_public, show_living_score) "
        f"SELECT estate_id, is_demo, is_public, show_living_score FROM estates "
        f"WHERE name IN ({_NAME_LIST})"
    )
    op.execute(
        f"UPDATE estates SET is_demo = true, is_public = false, show_living_score = false "
        f"WHERE estate_id IN (SELECT estate_id FROM {_TABLE})"
    )


def downgrade() -> None:
    op.execute(
        f"UPDATE estates AS estate SET is_demo = prior.is_demo, is_public = prior.is_public, "
        f"show_living_score = prior.show_living_score FROM {_TABLE} AS prior "
        f"WHERE estate.estate_id = prior.estate_id"
    )
    op.drop_table(_TABLE)
