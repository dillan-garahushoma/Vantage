"""Add the estate residency-request table (admin approval workflow).

One new, purely additive table. A row is one resident's request to be admitted to
one unit of one estate, plus the administrator who decided it and when. It is the
approval-based counterpart to redeeming a join code, which stays in place
unchanged - this migration does not touch ``estate_join_codes``,
``estate_memberships`` or their indexes.

Constraints come from ``app/identity/models/estate_residency_request.py`` so the
database enforces exactly what the service can produce:

* ``fk_estate_residency_requests_estate_id_estates`` ON DELETE RESTRICT - a
  decision record is estate history and does not vanish with the estate;
* ``fk_estate_residency_requests_user_id_users`` and ``..._decided_by_users`` ON
  DELETE SET NULL - deleting an account does not erase that a request was made or
  decided; the contact snapshot on the row survives either way;
* ``ck_estate_residency_requests_status`` - only the three vocabulary values;
* ``ck_estate_residency_requests_decided_at_present`` and
  ``..._pending_undecided`` - a pending request has no decision, a decided one
  always has a decision time;
* ``uq_estate_residency_requests_one_pending_per_user_estate`` - a partial unique
  index allowing at most one pending request per person per estate, so duplicates
  cannot be queued while a rejected applicant may still apply again;
* ``ix_estate_residency_requests_estate_id_status_created_at`` - the admin queue
  read: this estate's requests of a status, newest first.

The table is new, so every column starts NULL-free by construction and there is no
pre-flight check to fail; no existing row is read, moved or deleted.

Revision ID: e7a1b3c5d9f2
Revises: c3f7a1b9d4e2
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7a1b3c5d9f2"
down_revision: Union[str, Sequence[str], None] = "c3f7a1b9d4e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "estate_residency_requests",
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("estate_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("property_id", sa.Integer(), nullable=True),
        sa.Column("unit_no", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("applicant_name", sa.String(length=120), nullable=False),
        sa.Column("applicant_email", sa.String(length=320), nullable=False),
        sa.Column("applicant_phone", sa.String(length=32), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("decided_by", sa.Integer(), nullable=True),
        sa.Column("decided_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("decision_note", sa.String(length=500), nullable=True),
        sa.Column("notified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("decision_notified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("request_id"),
        sa.ForeignKeyConstraint(
            ["estate_id"],
            ["estates.estate_id"],
            name="fk_estate_residency_requests_estate_id_estates",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name="fk_estate_residency_requests_user_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.unit_id"],
            name="fk_estate_residency_requests_property_id_properties",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by"],
            ["users.user_id"],
            name="fk_estate_residency_requests_decided_by_users",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_estate_residency_requests_status",
        ),
        sa.CheckConstraint(
            "status = 'pending' OR decided_at IS NOT NULL",
            name="ck_estate_residency_requests_decided_at_present",
        ),
        sa.CheckConstraint(
            "status <> 'pending' OR decided_at IS NULL",
            name="ck_estate_residency_requests_pending_undecided",
        ),
    )
    op.create_index(
        "uq_estate_residency_requests_one_pending_per_user_estate",
        "estate_residency_requests",
        ["user_id", "estate_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_estate_residency_requests_estate_id_status_created_at",
        "estate_residency_requests",
        ["estate_id", "status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_estate_residency_requests_estate_id_status_created_at",
        table_name="estate_residency_requests",
    )
    op.drop_index(
        "uq_estate_residency_requests_one_pending_per_user_estate",
        table_name="estate_residency_requests",
    )
    op.drop_table("estate_residency_requests")
