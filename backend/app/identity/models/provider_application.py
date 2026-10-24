from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, Integer, String, TIMESTAMP, Text, text
from sqlalchemy.sql import func

from app.db.base import Base


class ProviderApplication(Base):
    __tablename__ = "provider_applications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_provider_applications_status",
        ),
        CheckConstraint(
            "status = 'pending' OR reviewed_at IS NOT NULL",
            name="ck_provider_applications_reviewed_at_present",
        ),
        Index(
            "uq_provider_applications_pending_estate_email",
            "estate_id",
            "email",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index(
            "ix_provider_applications_estate_status_created",
            "estate_id",
            "status",
            "created_at",
        ),
    )

    application_id = Column(Integer, primary_key=True)
    estate_id = Column(
        Integer, ForeignKey("estates.estate_id", ondelete="RESTRICT"), nullable=False
    )
    full_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    trade = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False)
    note = Column(String(500), nullable=True)
    status = Column(String(16), nullable=False, server_default="pending")
    reviewed_by_user_id = Column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
