from sqlalchemy import ForeignKeyConstraint, UniqueConstraint

from app.identity.models.estate_membership import EstateMembership
from app.property.models.estate import Estate
from app.property.models.property import Property
from app.property.repositories.property_repository import PropertyRepository


def test_property_supports_an_explicit_estate_foreign_key() -> None:
    estate_id = Property.__table__.c.estate_id

    assert estate_id.nullable is True
    assert any(
        isinstance(constraint, ForeignKeyConstraint)
        and {column.name for column in constraint.columns} == {"estate_id"}
        for constraint in Property.__table__.constraints
    )


def test_membership_models_a_user_estate_and_optional_property_scope() -> None:
    columns = EstateMembership.__table__.c

    assert columns.user_id.nullable is False
    assert columns.estate_id.nullable is False
    assert columns.property_id.nullable is True
    assert Estate.__tablename__ == "estates"
    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns}
        == {"user_id", "estate_id", "property_id"}
        for constraint in EstateMembership.__table__.constraints
    )


def test_property_repository_has_an_estate_scoped_lookup() -> None:
    assert hasattr(PropertyRepository, "get_by_id_in_estate")
