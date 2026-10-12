from sqlalchemy import Column, ForeignKey, Index, Integer, String, TIMESTAMP, UniqueConstraint, text
from sqlalchemy.sql import func

from app.db.base import Base


class EstateMembership(Base):
    """Explicit persisted relationship used to authorize estate-scoped access.

    A user may hold more than one unit membership in the same estate (ADR-002),
    so the scoped uniqueness rule is ``(user_id, estate_id, property_id)``.
    A membership created by redeeming a join code additionally records the code
    that produced it, and ``uq_membership_user_estate_join`` lets a self-service
    resident hold at most one such row per estate - which is the concurrency guard
    behind ``POST /api/v1/memberships/join``. Operator- and legacy-created rows
    (``join_code_id IS NULL``) keep the multi-unit behaviour.
    """

    __tablename__ = "estate_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "estate_id", "property_id", name="uq_membership_scope"),
        Index(
            "uq_estate_memberships_user_estate_null_property",
            "user_id",
            "estate_id",
            unique=True,
            postgresql_where=text("property_id IS NULL"),
        ),
        Index(
            "uq_membership_user_estate_join",
            "user_id",
            "estate_id",
            unique=True,
            postgresql_where=text("join_code_id IS NOT NULL"),
        ),
    )

    membership_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    estate_id = Column(Integer, ForeignKey("estates.estate_id", ondelete="CASCADE"), nullable=False)
    property_id = Column(
        Integer, ForeignKey("properties.unit_id", ondelete="CASCADE"), nullable=True
    )
    membership_role = Column(String(32), nullable=False)
    # The join code this membership was redeemed with; null for provisioning,
    # seeding and legacy rows. Nulled if the code row is ever removed.
    join_code_id = Column(
        Integer,
        ForeignKey("estate_join_codes.code_id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
