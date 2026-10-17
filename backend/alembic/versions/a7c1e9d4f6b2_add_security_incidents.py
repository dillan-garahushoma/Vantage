"""Add the intentionally limited security incident table.

One purely additive table for BATCH 6B. An incident exists to be the Living Score
security input: a count of incidents in an estate over a rolling window. It is
not a security-management platform, so there is no assignment, comment,
attachment, notification or workflow column, and no description field at all.

Constraints come from ``app/community/domain/incident_vocabulary.py``, so the
database refuses anything outside the controlled vocabulary that the API also
enforces:

* ``fk_security_incidents_estate_id_estates`` ON DELETE RESTRICT - operational
  history does not vanish when an estate is removed;
* ``fk_security_incidents_property_id_properties`` ON DELETE SET NULL - an
  incident may be estate-wide, and removing a unit must not erase history;
* ``fk_security_incidents_created_by_users`` ON DELETE SET NULL - the record
  survives the departure of the admin who filed it;
* ``ck_security_incidents_resolution_timestamps`` - a resolved incident has a
  resolution time, and only a resolved one does;
* ``ix_security_incidents_estate_id_occurred_at`` - the score's window query;
* ``ix_security_incidents_estate_id_status`` - the HOA "what is still open?"
  list.

The table is new, so every column starts NULL-free by construction and there is
no pre-flight check to fail; no existing row is read, moved or deleted.

Revision ID: a7c1e9d4f6b2
Revises: b8e5f2d1c3a4
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.community.domain.incident_vocabulary import (
    CATEGORIES,
    DEFAULT_STATUS,
    SEVERITIES,
    STATUSES,
    resolution_timestamps_check,
    sql_in,
)


revision: str = "a7c1e9d4f6b2"
down_revision: Union[str, Sequence[str], None] = "b8e5f2d1c3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "security_incidents",
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("estate_id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=DEFAULT_STATUS,
            nullable=False,
        ),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("incident_id"),
        sa.ForeignKeyConstraint(
            ["estate_id"],
            ["estates.estate_id"],
            name="fk_security_incidents_estate_id_estates",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.unit_id"],
            name="fk_security_incidents_property_id_properties",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.user_id"],
            name="fk_security_incidents_created_by_users",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(sql_in("category", CATEGORIES), name="ck_security_incidents_category"),
        sa.CheckConstraint(sql_in("severity", SEVERITIES), name="ck_security_incidents_severity"),
        sa.CheckConstraint(sql_in("status", STATUSES), name="ck_security_incidents_status"),
        sa.CheckConstraint(
            resolution_timestamps_check(),
            name="ck_security_incidents_resolution_timestamps",
        ),
    )
    op.create_index(
        "ix_security_incidents_estate_id_occurred_at",
        "security_incidents",
        ["estate_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_security_incidents_estate_id_status",
        "security_incidents",
        ["estate_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_security_incidents_estate_id_status", table_name="security_incidents")
    op.drop_index("ix_security_incidents_estate_id_occurred_at", table_name="security_incidents")
    op.drop_table("security_incidents")
