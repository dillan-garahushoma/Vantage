"""Add estate join codes and the membership event log.

BATCH ONB-2. Three additive, non-destructive changes:

1. ``estate_join_codes`` - the shareable secret an HOA admin gives a resident.
   ``code`` is unique for all time, so a revoked or leaked code can never become
   valid again, and a partial unique index on ``estate_id WHERE revoked_at IS
   NULL`` allows at most one live code per estate, so rotation cannot leave two.
2. ``estate_membership_events`` - the append-only audit of joins and removals.
   Metadata only: no free-text column and no personal data beyond user ids.
3. ``estate_memberships.join_code_id`` plus the partial unique index
   ``uq_membership_user_estate_join``.

**Deviation from the batch, on purpose.** The batch asked for a full unique index
``uq_membership_user_estate`` on ``estate_memberships (user_id, estate_id)`` and a
pre-check that fails when duplicates exist. That invariant contradicts the code
as it stands, so it was not added:

* ADR-002 and the existing fixtures support a resident holding more than one unit
  membership in one estate (``tests/factories.py`` gives ``resident_a1`` two, and
  ``test_batch_b_authorization.py`` asserts two ``property_ids``);
* ``app/seed_demo.py`` deliberately gives Thandi two units in one estate, and the
  batch forbids touching that file. The requested pre-check would therefore make
  this very migration *fail* on the demo database, and re-seeding would then break
  on the new constraint.

The smallest correct thing that still delivers the batch's intent - a resident
cannot join the same estate twice, and a concurrent duplicate is a 409 rather
than a 500 - is to scope the uniqueness to the self-service path via the new
``join_code_id`` column. It is NULL for every existing row, so this migration
needs no pre-check and cannot fail on a populated database: a new nullable column
with a NULL predicate cannot create a duplicate. Operator-provisioned and seeded
multi-unit memberships are unaffected.

Both new tables start empty and every existing row is untouched, so the upgrade is
safe to run while the application is live.

Revision ID: b1e4f7a9c2d5
Revises: d9f2a4c7e1b3
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1e4f7a9c2d5"
down_revision: Union[str, Sequence[str], None] = "d9f2a4c7e1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "estate_join_codes",
        sa.Column("code_id", sa.Integer(), nullable=False),
        sa.Column("estate_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=12), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["estate_id"],
            ["estates.estate_id"],
            name="fk_estate_join_codes_estate_id_estates",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.user_id"],
            name="fk_estate_join_codes_created_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("code_id"),
        sa.UniqueConstraint("code", name="uq_estate_join_codes_code"),
    )
    op.create_index(
        "uq_estate_join_codes_one_active_per_estate",
        "estate_join_codes",
        ["estate_id"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )

    op.create_table(
        "estate_membership_events",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("estate_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("membership_role", sa.String(length=32), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "occurred_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ('joined', 'removed')",
            name="ck_estate_membership_events_type_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["estate_id"],
            ["estates.estate_id"],
            name="fk_estate_membership_events_estate_id_estates",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name="fk_estate_membership_events_user_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.unit_id"],
            name="fk_estate_membership_events_property_id_properties",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.user_id"],
            name="fk_estate_membership_events_actor_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_estate_membership_events_estate_id_occurred_at",
        "estate_membership_events",
        ["estate_id", "occurred_at"],
        unique=False,
    )

    op.add_column(
        "estate_memberships", sa.Column("join_code_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_estate_memberships_join_code_id_estate_join_codes",
        "estate_memberships",
        "estate_join_codes",
        ["join_code_id"],
        ["code_id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_membership_user_estate_join",
        "estate_memberships",
        ["user_id", "estate_id"],
        unique=True,
        postgresql_where=sa.text("join_code_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_membership_user_estate_join", table_name="estate_memberships")
    op.drop_constraint(
        "fk_estate_memberships_join_code_id_estate_join_codes",
        "estate_memberships",
        type_="foreignkey",
    )
    op.drop_column("estate_memberships", "join_code_id")

    op.drop_index(
        "ix_estate_membership_events_estate_id_occurred_at",
        table_name="estate_membership_events",
    )
    op.drop_table("estate_membership_events")

    op.drop_index(
        "uq_estate_join_codes_one_active_per_estate", table_name="estate_join_codes"
    )
    op.drop_table("estate_join_codes")
