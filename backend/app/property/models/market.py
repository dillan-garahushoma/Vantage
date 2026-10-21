"""Current marketing workflows; deliberately separate from legacy listings/sales."""
from sqlalchemy import (CheckConstraint, Column, Date, ForeignKey, Index, Integer,
                        Numeric, String, Text, TIMESTAMP, UniqueConstraint, text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db.base import Base


class MarketingAuthority(Base):
    __tablename__ = 'marketing_authorities'
    __table_args__ = (
        Index('uq_marketing_authority_active_unit', 'estate_id', 'property_id', unique=True,
              postgresql_where=text('revoked_at IS NULL')),
        Index('ix_marketing_authority_estate_representative', 'estate_id', 'representative_id'),
    )
    authority_id = Column(Integer, primary_key=True)
    estate_id = Column(Integer, ForeignKey('estates.estate_id', ondelete='RESTRICT'), nullable=False)
    property_id = Column(Integer, ForeignKey('properties.unit_id', ondelete='RESTRICT'), nullable=False)
    representative_id = Column(Integer, ForeignKey('users.user_id', ondelete='RESTRICT'), nullable=False)
    verified_by = Column(Integer, ForeignKey('users.user_id', ondelete='RESTRICT'), nullable=False)
    verification_reference = Column(String(240), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(TIMESTAMP(timezone=True), nullable=True)
    revoked_by = Column(Integer, ForeignKey('users.user_id', ondelete='RESTRICT'), nullable=True)


class MarketingRequest(Base):
    __tablename__ = 'marketing_requests'
    __table_args__ = (
        CheckConstraint("purpose IN ('sale','rent')", name='ck_marketing_request_purpose'),
        CheckConstraint("status IN ('pending','approved','rejected','listed','cancelled','fulfilled')", name='ck_marketing_request_status'),
        CheckConstraint('requested_price > 0', name='ck_marketing_request_price'),
        Index('uq_marketing_request_open_unit', 'estate_id', 'property_id', unique=True,
              postgresql_where=text("status IN ('pending','approved','listed')")),
        Index('ix_marketing_request_estate_requester', 'estate_id', 'requester_id', 'request_id'),
        Index('ix_marketing_request_estate_agent', 'estate_id', 'agent_id', 'request_id'),
    )
    request_id = Column(Integer, primary_key=True)
    estate_id = Column(Integer, ForeignKey('estates.estate_id', ondelete='RESTRICT'), nullable=False)
    property_id = Column(Integer, ForeignKey('properties.unit_id', ondelete='RESTRICT'), nullable=False)
    authority_id = Column(Integer, ForeignKey('marketing_authorities.authority_id', ondelete='RESTRICT'), nullable=False)
    requester_id = Column(Integer, ForeignKey('users.user_id', ondelete='RESTRICT'), nullable=False)
    purpose = Column(String(10), nullable=False)
    requested_price = Column(Numeric(12, 2), nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(16), nullable=False, default='pending')
    agent_id = Column(Integer, ForeignKey('users.user_id', ondelete='RESTRICT'), nullable=True)
    decision_reason = Column(Text, nullable=True)
    decided_by = Column(Integer, ForeignKey('users.user_id', ondelete='RESTRICT'), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    decided_at = Column(TIMESTAMP(timezone=True), nullable=True)


class MarketListing(Base):
    __tablename__ = 'market_listings'
    __table_args__ = (
        UniqueConstraint('request_id', name='uq_market_listing_request'),
        CheckConstraint("purpose IN ('sale','rent')", name='ck_market_listing_purpose'),
        CheckConstraint("status IN ('draft','active','withdrawn','sold','let')", name='ck_market_listing_status'),
        CheckConstraint('asking_price > 0 AND version > 0', name='ck_market_listing_price_version'),
        Index('ix_market_listing_estate_status', 'estate_id', 'status', 'listing_id'),
    )
    listing_id = Column(Integer, primary_key=True)
    estate_id = Column(Integer, ForeignKey('estates.estate_id', ondelete='RESTRICT'), nullable=False)
    property_id = Column(Integer, ForeignKey('properties.unit_id', ondelete='RESTRICT'), nullable=False)
    request_id = Column(Integer, ForeignKey('marketing_requests.request_id', ondelete='RESTRICT'), nullable=False)
    purpose = Column(String(10), nullable=False)
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=False)
    asking_price = Column(Numeric(12, 2), nullable=False)
    status = Column(String(16), nullable=False, default='draft')
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    published_at = Column(TIMESTAMP(timezone=True), nullable=True)


class ListingPriceEvent(Base):
    __tablename__ = 'listing_price_events'
    __table_args__ = (
        UniqueConstraint('listing_id', 'listing_version', name='uq_listing_price_version'),
        CheckConstraint('new_price > 0 AND (old_price IS NULL OR old_price > 0)', name='ck_listing_price_positive'),
        Index('ix_listing_price_estate_listing', 'estate_id', 'listing_id', 'price_id'),
    )
    price_id = Column(Integer, primary_key=True)
    estate_id = Column(Integer, ForeignKey('estates.estate_id', ondelete='RESTRICT'), nullable=False)
    listing_id = Column(Integer, ForeignKey('market_listings.listing_id', ondelete='RESTRICT'), nullable=False)
    old_price = Column(Numeric(12, 2), nullable=True)
    new_price = Column(Numeric(12, 2), nullable=False)
    changed_by = Column(Integer, ForeignKey('users.user_id', ondelete='RESTRICT'), nullable=False)
    reason = Column(Text, nullable=False)
    listing_version = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)


class MarketTransaction(Base):
    __tablename__ = 'market_transactions'
    __table_args__ = (
        UniqueConstraint('listing_id', name='uq_market_transaction_listing'),
        CheckConstraint("purpose IN ('sale','rent')", name='ck_market_transaction_purpose'),
        CheckConstraint('actual_amount > 0 AND asking_price_at_completion > 0', name='ck_market_transaction_amount'),
        Index('ix_market_transaction_estate_purpose', 'estate_id', 'purpose', 'transaction_id'),
    )
    transaction_id = Column(Integer, primary_key=True)
    estate_id = Column(Integer, ForeignKey('estates.estate_id', ondelete='RESTRICT'), nullable=False)
    property_id = Column(Integer, ForeignKey('properties.unit_id', ondelete='RESTRICT'), nullable=False)
    listing_id = Column(Integer, ForeignKey('market_listings.listing_id', ondelete='RESTRICT'), nullable=False)
    purpose = Column(String(10), nullable=False)
    actual_amount = Column(Numeric(12, 2), nullable=False)
    asking_price_at_completion = Column(Numeric(12, 2), nullable=False)
    effective_date = Column(Date, nullable=False)
    recorded_by = Column(Integer, ForeignKey('users.user_id', ondelete='RESTRICT'), nullable=False)
    reference = Column(String(240), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)


class MarketEvent(Base):
    __tablename__ = 'market_events'
    __table_args__ = (Index('ix_market_event_estate_entity', 'estate_id', 'entity_type', 'entity_id', 'event_id'),)
    event_id = Column(Integer, primary_key=True)
    estate_id = Column(Integer, ForeignKey('estates.estate_id', ondelete='RESTRICT'), nullable=False)
    entity_type = Column(String(20), nullable=False)
    entity_id = Column(Integer, nullable=False)
    action = Column(String(30), nullable=False)
    actor_id = Column(Integer, ForeignKey('users.user_id', ondelete='RESTRICT'), nullable=False)
    details = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
