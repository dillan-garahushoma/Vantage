"""Immutable operational briefing versions, independent of score availability."""
from sqlalchemy import Column, ForeignKey, Index, Integer, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db.base import Base


class IntelligenceBriefing(Base):
    __tablename__ = 'intelligence_briefings'
    __table_args__ = (Index('ix_intelligence_briefings_estate_created', 'estate_id', 'created_at', 'briefing_id'),)

    briefing_id = Column(Integer, primary_key=True)
    estate_id = Column(Integer, ForeignKey('estates.estate_id', ondelete='RESTRICT'), nullable=False)
    created_by = Column(Integer, ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True)
    template_version = Column(String(40), nullable=False)
    data_origin = Column(String(10), nullable=False)
    facts = Column(JSONB, nullable=False)
    output = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
