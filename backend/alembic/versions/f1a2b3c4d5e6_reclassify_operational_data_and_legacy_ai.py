"""Reclassify legacy seeded UI data without deleting operational history.

The former local setup stamped real estate records as demonstration data and
pre-populated AI triage rows. Those rows are retained for traceability, but are
marked as seeded so they cannot appear as a user-requested AI result. An explicit
new triage request replaces its labels in-place after the provider returns a
validated result; no request is made during this migration.

Revision ID: f1a2b3c4d5e6
Revises: e7a1b3c5d9f2
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e7a1b3c5d9f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keep the exact pre-migration estate set so a downgrade can restore only
    # the classifications this revision changed. This is intentionally not an
    # application table; it exists solely to make the data migration reversible.
    op.create_table(
        "migration_f1a2b3c4d5e6_demo_estates",
        sa.Column("estate_id", sa.Integer(), primary_key=True),
    )
    op.execute(
        "INSERT INTO migration_f1a2b3c4d5e6_demo_estates (estate_id) "
        "SELECT estate_id FROM estates WHERE is_demo = true"
    )
    op.add_column(
        "complaint_ai_suggestions",
        sa.Column("is_seeded", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    # Existing rows predate user-triggered triage. Preserve them while making
    # their simulated provenance explicit; the application ignores them until a
    # user explicitly requests a fresh suggestion.
    op.execute("UPDATE complaint_ai_suggestions SET is_seeded = true")
    # Operational data is now the product's source of truth, regardless of how
    # it first entered the local database. This changes classification only.
    op.execute("UPDATE estates SET is_demo = false WHERE is_demo = true")


def downgrade() -> None:
    op.execute(
        "UPDATE estates SET is_demo = true "
        "WHERE estate_id IN (SELECT estate_id "
        "FROM migration_f1a2b3c4d5e6_demo_estates)"
    )
    op.drop_column("complaint_ai_suggestions", "is_seeded")
    op.drop_table("migration_f1a2b3c4d5e6_demo_estates")
