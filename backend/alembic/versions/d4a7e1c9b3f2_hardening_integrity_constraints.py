"""Hardening Pass H: data integrity constraints and relationship protection.

Revision ID: d4a7e1c9b3f2
Revises: c3f9a6d4e1b2
Create Date: 2026-10-08 12:46:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4a7e1c9b3f2"
down_revision: Union[str, None] = "c3f9a6d4e1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Pre-migration safety checks (run only in online/live mode)
    if conn is not None and not op.get_context().as_sql:
        # Check duplicate (estate_id, unit_no) in properties
        res = conn.execute(sa.text("""
            SELECT estate_id, unit_no, count(*)
            FROM properties
            WHERE estate_id IS NOT NULL
            GROUP BY estate_id, unit_no
            HAVING count(*) > 1
        """)).fetchall()
        if res:
            raise RuntimeError(f"Cannot apply migration: duplicate unit numbers within estate found: {res}")

        # Check duplicate unit_no for legacy properties
        res = conn.execute(sa.text("""
            SELECT unit_no, count(*)
            FROM properties
            WHERE estate_id IS NULL
            GROUP BY unit_no
            HAVING count(*) > 1
        """)).fetchall()
        if res:
            raise RuntimeError(f"Cannot apply migration: duplicate legacy unit numbers found: {res}")

        # Check duplicate (user_id, estate_id) in estate_memberships where property_id is null
        res = conn.execute(sa.text("""
            SELECT user_id, estate_id, count(*)
            FROM estate_memberships
            WHERE property_id IS NULL
            GROUP BY user_id, estate_id
            HAVING count(*) > 1
        """)).fetchall()
        if res:
            raise RuntimeError(f"Cannot apply migration: duplicate estate-level memberships found: {res}")

        # Check orphaned complaints.unit_id
        res = conn.execute(sa.text("""
            SELECT c.complaint_id, c.unit_id
            FROM complaints c
            LEFT JOIN properties p ON c.unit_id = p.unit_id
            WHERE p.unit_id IS NULL
        """)).fetchall()
        if res:
            raise RuntimeError(f"Cannot apply migration: orphaned complaint unit_ids found: {res}")

        # Check orphaned maintenance_work_orders.provider_id
        res = conn.execute(sa.text("""
            SELECT w.work_order_id, w.provider_id
            FROM maintenance_work_orders w
            LEFT JOIN service_providers sp ON w.provider_id = sp.provider_id
            WHERE sp.provider_id IS NULL
        """)).fetchall()
        if res:
            raise RuntimeError(f"Cannot apply migration: orphaned work order provider_ids found: {res}")

        # Check orphaned reviews.user_id
        res = conn.execute(sa.text("""
            SELECT r.review_id, r.user_id
            FROM reviews r
            LEFT JOIN users u ON r.user_id = u.user_id
            WHERE u.user_id IS NULL
        """)).fetchall()
        if res:
            raise RuntimeError(f"Cannot apply migration: orphaned review user_ids found: {res}")

        # Check duplicate active work orders per complaint
        res = conn.execute(sa.text("""
            SELECT complaint_id, count(*)
            FROM maintenance_work_orders
            WHERE status <> 'cancelled'
            GROUP BY complaint_id
            HAVING count(*) > 1
        """)).fetchall()
        if res:
            raise RuntimeError(f"Cannot apply migration: multiple active work orders per complaint found: {res}")

        # Check invalid resident_rating
        res = conn.execute(sa.text("""
            SELECT work_order_id, resident_rating
            FROM maintenance_work_orders
            WHERE resident_rating IS NOT NULL AND (resident_rating < 1 OR resident_rating > 5)
        """)).fetchall()
        if res:
            raise RuntimeError(f"Cannot apply migration: invalid resident ratings found: {res}")

        # Check invalid priority
        res = conn.execute(sa.text("""
            SELECT complaint_id, priority
            FROM complaints
            WHERE priority NOT IN ('low', 'normal', 'high', 'urgent')
        """)).fetchall()
        if res:
            raise RuntimeError(f"Cannot apply migration: invalid complaint priorities found: {res}")

    # 1. Properties: drop global unit_no unique constraint, add scoped unique and partial legacy index
    op.execute("ALTER TABLE properties DROP CONSTRAINT IF EXISTS properties_unit_no_key")
    op.create_unique_constraint("uq_properties_estate_unit_no", "properties", ["estate_id", "unit_no"])
    op.create_index(
        "uq_properties_legacy_unit_no",
        "properties",
        ["unit_no"],
        unique=True,
        postgresql_where=sa.text("estate_id IS NULL"),
    )

    # 2. Estate Memberships: partial unique index for user-estate where property_id is null
    op.create_index(
        "uq_estate_memberships_user_estate_null_property",
        "estate_memberships",
        ["user_id", "estate_id"],
        unique=True,
        postgresql_where=sa.text("property_id IS NULL"),
    )

    # 3. Missing Foreign Keys (ON DELETE RESTRICT)
    op.create_foreign_key(
        "fk_complaints_unit_id_properties",
        "complaints",
        "properties",
        ["unit_id"],
        ["unit_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_work_orders_provider_id_service_providers",
        "maintenance_work_orders",
        "service_providers",
        ["provider_id"],
        ["provider_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_reviews_user_id_users",
        "reviews",
        "users",
        ["user_id"],
        ["user_id"],
        ondelete="RESTRICT",
    )

    # 4. One active work order per complaint
    op.create_index(
        "uq_active_work_order_per_complaint",
        "maintenance_work_orders",
        ["complaint_id"],
        unique=True,
        postgresql_where=sa.text("status <> 'cancelled'"),
    )

    # 5. Check constraints
    op.create_check_constraint(
        "ck_work_orders_resident_rating_1_to_5",
        "maintenance_work_orders",
        "resident_rating IS NULL OR (resident_rating >= 1 AND resident_rating <= 5)",
    )
    op.create_check_constraint(
        "ck_complaints_priority_allowed",
        "complaints",
        "priority IN ('low', 'normal', 'high', 'urgent')",
    )


def downgrade() -> None:
    # 5. Drop check constraints
    op.drop_constraint("ck_complaints_priority_allowed", "complaints", type_="check")
    op.drop_constraint("ck_work_orders_resident_rating_1_to_5", "maintenance_work_orders", type_="check")

    # 4. Drop active work order unique index
    op.drop_index("uq_active_work_order_per_complaint", table_name="maintenance_work_orders")

    # 3. Drop foreign keys
    op.drop_constraint("fk_reviews_user_id_users", "reviews", type_="foreignkey")
    op.drop_constraint("fk_work_orders_provider_id_service_providers", "maintenance_work_orders", type_="foreignkey")
    op.drop_constraint("fk_complaints_unit_id_properties", "complaints", type_="foreignkey")

    # 2. Drop membership uniqueness partial index
    op.drop_index("uq_estate_memberships_user_estate_null_property", table_name="estate_memberships")

    # 1. Properties: drop partial legacy index and scoped constraint, restore global unit_no unique
    op.drop_index("uq_properties_legacy_unit_no", table_name="properties")
    op.drop_constraint("uq_properties_estate_unit_no", "properties", type_="unique")
    op.create_unique_constraint("properties_unit_no_key", "properties", ["unit_no"])
