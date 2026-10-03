from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text, TIMESTAMP
from sqlalchemy.sql import func

from app.db.base import Base


class MaintenanceworkOrder(Base):
    __tablename__ = "maintenance_work_orders"

    work_order_id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.complaint_id", ondelete="CASCADE"), nullable=False)
    provider_id = Column(Integer, nullable=False)
    assigned_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    resolved_at = Column(TIMESTAMP(timezone=True), nullable=True)
    job_cost = Column(Numeric(12, 2), nullable=True)
    resident_rating = Column(Integer, nullable=True)
    completion_notes = Column(Text, nullable=True)
    status = Column(String(20), default="assigned")
    estimated_completion_date = Column(TIMESTAMP(timezone=True), nullable=True)
    actual_completion_date = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
