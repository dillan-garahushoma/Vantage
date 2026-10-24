from sqlalchemy import Column, ForeignKey, Index, Integer, String, TIMESTAMP, text
from sqlalchemy.sql import func

from app.db.base import Base


class ProviderInvitation(Base):
    __tablename__ = "provider_invitations"
    __table_args__ = (
        Index(
            "uq_provider_invitations_active_estate_email",
            "estate_id",
            "email",
            unique=True,
            postgresql_where=text("accepted_at IS NULL AND revoked_at IS NULL"),
        ),
        Index("ix_provider_invitations_token_digest", "token_digest", unique=True),
    )

    invitation_id = Column(Integer, primary_key=True)
    application_id = Column(
        Integer,
        ForeignKey("provider_applications.application_id", ondelete="RESTRICT"),
        nullable=False,
    )
    estate_id = Column(
        Integer, ForeignKey("estates.estate_id", ondelete="CASCADE"), nullable=False
    )
    created_by_user_id = Column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    email = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    trade = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False)
    token_digest = Column(String(64), nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    accepted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    revoked_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
