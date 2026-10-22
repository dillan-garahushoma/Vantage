"""Account preferences, expiring recovery grants and private operational notices."""
from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, TIMESTAMP, text
from sqlalchemy.sql import func
from app.db.base import Base


class AccountPreference(Base):
    __tablename__ = 'account_preferences'
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
    maintenance_notifications = Column(Boolean, nullable=False, server_default=text('true'))


class RecoveryGrant(Base):
    __tablename__ = 'recovery_grants'
    grant_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    token_digest = Column(String(64), nullable=False, unique=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    used_at = Column(TIMESTAMP(timezone=True))


class OperationalNotification(Base):
    __tablename__ = 'operational_notifications'
    __table_args__ = (Index('ix_notifications_estate_user_id', 'estate_id', 'user_id', 'notification_id'),)
    notification_id = Column(Integer, primary_key=True)
    estate_id = Column(Integer, ForeignKey('estates.estate_id', ondelete='RESTRICT'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    kind = Column(String(40), nullable=False)
    resource_id = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    read_at = Column(TIMESTAMP(timezone=True))
