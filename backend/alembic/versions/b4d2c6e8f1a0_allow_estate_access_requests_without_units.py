"""Allow estate access requests before a unit is assigned.

Revision ID: b4d2c6e8f1a0
Revises: c5a7d9e1f3b2, f3a6b2c9d1e4
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4d2c6e8f1a0"
down_revision: Union[str, Sequence[str], None] = (
    "c5a7d9e1f3b2",
    "f3a6b2c9d1e4",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "estate_residency_requests",
        "unit_no",
        existing_type=sa.String(length=10),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "estate_residency_requests",
        "unit_no",
        existing_type=sa.String(length=10),
        nullable=False,
    )
