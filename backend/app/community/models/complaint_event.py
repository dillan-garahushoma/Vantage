from sqlalchemy import Column, ForeignKey, Integer, String, Text, TIMESTAMP
from sqlalchemy.sql import func

from app.db.base import Base


class ComplaintEvent(Base):
    """Append-only operational evidence for a complaint lifecycle transition."""

    __tablename__ = "complaint_events"

    event_id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(
        Integer, ForeignKey("complaints.complaint_id", ondelete="CASCADE"), nullable=False
    )
    estate_id = Column(Integer, ForeignKey("estates.estate_id", ondelete="RESTRICT"), nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String(40), nullable=False)
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=True)
    note = Column(Text, nullable=True)
    occurred_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
