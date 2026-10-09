from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, Integer, Numeric, String, Text, TIMESTAMP, text
from sqlalchemy.sql import func

from app.db.base import Base


class MaintenanceworkOrder(Base):
    __tablename__ = "maintenance_work_orders"
    __table_args__ = (
        Index(
            "uq_active_work_order_per_complaint",
            "complaint_id",
            unique=True,
            postgresql_where=text("status <> 'cancelled'"),
        ),
        CheckConstraint(
            "resident_rating IS NULL OR (resident_rating >= 1 AND resident_rating <= 5)",
            name="ck_work_orders_resident_rating_1_to_5",
        ),
    )

    work_order_id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.complaint_id", ondelete="CASCADE"), nullable=False)
    estate_id = Column(Integer, ForeignKey("estates.estate_id", ondelete="RESTRICT"), nullable=True)
    provider_id = Column(Integer, ForeignKey("service_providers.provider_id", ondelete="RESTRICT"), nullable=False)
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
