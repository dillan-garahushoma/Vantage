from sqlalchemy import Column, ForeignKey, Integer, String, TIMESTAMP, UniqueConstraint
from sqlalchemy.sql import func

from app.db.base import Base


class EstateMembership(Base):
    """Explicit persisted relationship used to authorize estate-scoped access."""

    __tablename__ = "estate_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "estate_id", "property_id", name="uq_membership_scope"),
    )

    membership_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    estate_id = Column(Integer, ForeignKey("estates.estate_id", ondelete="CASCADE"), nullable=False)
    property_id = Column(
        Integer, ForeignKey("properties.unit_id", ondelete="CASCADE"), nullable=True
    )
    membership_role = Column(String(32), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
