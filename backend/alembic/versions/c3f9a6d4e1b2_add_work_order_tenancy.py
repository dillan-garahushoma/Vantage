"""Link provider profiles to identities and scope work orders to estates.

Revision ID: c3f9a6d4e1b2
Revises: b2e8f5c3d0a1
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3f9a6d4e1b2"
down_revision: Union[str, Sequence[str], None] = "b2e8f5c3d0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("service_providers", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_service_providers_user_id_users", "service_providers", "users", ["user_id"], ["user_id"], ondelete="SET NULL"
    )
    op.create_unique_constraint("uq_service_providers_user_id", "service_providers", ["user_id"])
    op.add_column("maintenance_work_orders", sa.Column("estate_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_work_orders_estate_id_estates", "maintenance_work_orders", "estates", ["estate_id"], ["estate_id"], ondelete="RESTRICT"
    )
    op.create_index("ix_work_orders_estate_id", "maintenance_work_orders", ["estate_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_work_orders_estate_id", table_name="maintenance_work_orders")
    op.drop_constraint("fk_work_orders_estate_id_estates", "maintenance_work_orders", type_="foreignkey")
    op.drop_column("maintenance_work_orders", "estate_id")
    op.drop_constraint("uq_service_providers_user_id", "service_providers", type_="unique")
    op.drop_constraint("fk_service_providers_user_id_users", "service_providers", type_="foreignkey")
    op.drop_column("service_providers", "user_id")
