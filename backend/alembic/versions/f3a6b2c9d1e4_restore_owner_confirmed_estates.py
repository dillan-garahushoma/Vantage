"""Restore the owner-confirmed estates to their published, live classification.

The preceding migration retained the affected estate flags so this repair can
be limited to the five known estate identities and reversed without disturbing
their operational records or any other estate.

Revision ID: f3a6b2c9d1e4
Revises: e2f4c8b1a9d3
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a6b2c9d1e4"
down_revision: Union[str, Sequence[str], None] = "e2f4c8b1a9d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_BACKUP_TABLE = "migration_f3a6b2c9d1e4_estate_flags"
_NAMES = (
    "Silverleaf Reserve",
    "Willowbrook Mews",
    "Lakeside Gardens",
    "Eastbank Court",
    "Quarry View Flats",
)
_NAME_LIST = ", ".join(repr(name) for name in _NAMES)
_STALE_ESTATE_MATCH = (
    "name = 'musgrave' AND suburb = 'pinetown' AND city = 'durban' "
    "AND province = 'KwaZulu-Natal'"
)


def upgrade() -> None:
    op.create_table(
        _BACKUP_TABLE,
        sa.Column("estate_id", sa.Integer(), primary_key=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("show_living_score", sa.Boolean(), nullable=False),
    )
    op.execute(
        f"INSERT INTO {_BACKUP_TABLE} "
        "(estate_id, is_demo, is_public, show_living_score) "
        "SELECT estate_id, is_demo, is_public, show_living_score FROM estates "
        f"WHERE name IN ({_NAME_LIST}) OR ({_STALE_ESTATE_MATCH})"
    )
    op.execute(
        f"UPDATE estates AS estate SET is_demo = false, is_public = true, "
        "show_living_score = COALESCE(original.show_living_score, "
        "estate.show_living_score) "
        f"FROM migration_e2f4c8b1a9d3_seed_estate_flags AS original "
        f"WHERE estate.estate_id = original.estate_id "
        f"AND estate.name IN ({_NAME_LIST})"
    )
    op.execute(
        f"UPDATE estates SET is_public = false "
        f"WHERE {_STALE_ESTATE_MATCH} AND is_public = true"
    )


def downgrade() -> None:
    op.execute(
        f"UPDATE estates AS estate SET is_demo = prior.is_demo, "
        "is_public = prior.is_public, "
        "show_living_score = prior.show_living_score "
        f"FROM {_BACKUP_TABLE} AS prior "
        "WHERE estate.estate_id = prior.estate_id"
    )
    op.drop_table(_BACKUP_TABLE)
