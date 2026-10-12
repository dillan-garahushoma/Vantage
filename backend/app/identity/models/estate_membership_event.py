from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    TIMESTAMP,
)
from sqlalchemy.sql import func

from app.db.base import Base


class EstateMembershipEvent(Base):
    """Append-only audit of membership joins and removals.

    Metadata only: which estate, which user, under which membership role, for
    which unit, and who acted. There is deliberately no free-text column and no
    personal data beyond the user ids, so the table is safe to keep for the life
    of the estate - which is what the domain rule about operational event
    preservation requires.

    Rows are never updated or deleted: the repository exposes only ``record`` and
    ``list_for_estate``. ``ondelete="SET NULL"`` on the user columns means a
    deleted account leaves the history intact rather than erasing it.
    """

    __tablename__ = "estate_membership_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('joined', 'removed')",
            name="ck_estate_membership_events_type_allowed",
        ),
        Index(
            "ix_estate_membership_events_estate_id_occurred_at",
            "estate_id",
            "occurred_at",
        ),
    )

    event_id = Column(Integer, primary_key=True, index=True)
    estate_id = Column(
        Integer, ForeignKey("estates.estate_id", ondelete="RESTRICT"), nullable=False
    )
    user_id = Column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    membership_role = Column(String(32), nullable=False)
    property_id = Column(
        Integer, ForeignKey("properties.unit_id", ondelete="SET NULL"), nullable=True
    )
    event_type = Column(String(16), nullable=False)
    actor_user_id = Column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    occurred_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
