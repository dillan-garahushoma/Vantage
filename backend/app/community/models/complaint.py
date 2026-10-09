from sqlalchemy import Boolean, CheckConstraint, Column, ForeignKey, Integer, String, Text, TIMESTAMP
from sqlalchemy.sql import func

from app.db.base import Base


class Complaint(Base):
    __tablename__ = "complaints"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_complaints_priority_allowed",
        ),
    )

    complaint_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    estate_id = Column(Integer, ForeignKey("estates.estate_id", ondelete="RESTRICT"), nullable=True)
    unit_id = Column(Integer, ForeignKey("properties.unit_id", ondelete="RESTRICT"), nullable=False)
    category = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False, server_default="normal")
    is_anonymous = Column(Boolean, default=False)
    status = Column(String(20), default="submitted")
    assigned_to = Column(String(100), nullable=True)
    reviewed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    assigned_at = Column(TIMESTAMP(timezone=True), nullable=True)
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    resolved_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
