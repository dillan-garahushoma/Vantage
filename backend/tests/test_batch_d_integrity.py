import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, UniqueConstraint

from app.community.models.complaint import Complaint
from app.community.models.maintenance_work_order import MaintenanceworkOrder
from app.identity.models.estate_membership import EstateMembership
from app.property.models.property import Property
from app.property.repositories.property_repository import PropertyRepository
from app.providers.models.review import Review


def test_property_integrity_constraints() -> None:
    # 1. Scoped unique constraint (estate_id, unit_no)
    uq_names = {c.name for c in Property.__table__.constraints if isinstance(c, UniqueConstraint)}
    assert "uq_properties_estate_unit_no" in uq_names

    # 2. Legacy unit partial index
    index_names = {idx.name for idx in Property.__table__.indexes}
    assert "uq_properties_legacy_unit_no" in index_names

    # 3. Repository method
    assert hasattr(PropertyRepository, "get_by_unit_no_in_estate")


def test_estate_membership_integrity_constraints() -> None:
    index_names = {idx.name for idx in EstateMembership.__table__.indexes}
    assert "uq_estate_memberships_user_estate_null_property" in index_names


def test_complaint_foreign_key_and_priority_check() -> None:
    # FK unit_id -> properties.unit_id with ondelete="RESTRICT"
    unit_fk = next(
        fk for fk in Complaint.__table__.foreign_keys if fk.parent.name == "unit_id"
    )
    assert unit_fk.target_fullname == "properties.unit_id"
    assert unit_fk.ondelete == "RESTRICT"

    # Priority check constraint
    check_names = {c.name for c in Complaint.__table__.constraints if isinstance(c, CheckConstraint)}
    assert "ck_complaints_priority_allowed" in check_names


def test_maintenance_work_order_integrity_constraints() -> None:
    # FK provider_id -> service_providers.provider_id with ondelete="RESTRICT"
    provider_fk = next(
        fk for fk in MaintenanceworkOrder.__table__.foreign_keys if fk.parent.name == "provider_id"
    )
    assert provider_fk.target_fullname == "service_providers.provider_id"
    assert provider_fk.ondelete == "RESTRICT"

    # Rating check constraint
    check_names = {c.name for c in MaintenanceworkOrder.__table__.constraints if isinstance(c, CheckConstraint)}
    assert "ck_work_orders_resident_rating_1_to_5" in check_names

    # Partial unique index for active work order per complaint
    index_names = {idx.name for idx in MaintenanceworkOrder.__table__.indexes}
    assert "uq_active_work_order_per_complaint" in index_names


def test_review_foreign_key_user_restrict() -> None:
    user_fk = next(
        fk for fk in Review.__table__.foreign_keys if fk.parent.name == "user_id"
    )
    assert user_fk.target_fullname == "users.user_id"
    assert user_fk.ondelete == "RESTRICT"
