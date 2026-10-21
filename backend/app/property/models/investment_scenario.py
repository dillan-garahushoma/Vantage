"""Private immutable assumption/result snapshots. Revisions add rows."""
from sqlalchemy import Column, ForeignKey, Index, Integer, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db.base import Base


class InvestmentScenario(Base):
    __tablename__ = 'investment_scenarios'
    __table_args__ = (Index('ix_investment_scenarios_estate_owner_created', 'estate_id', 'owner_id', 'created_at', 'scenario_id'),)

    scenario_id = Column(Integer, primary_key=True)
    estate_id = Column(Integer, ForeignKey('estates.estate_id', ondelete='RESTRICT'), nullable=False)
    property_id = Column(Integer, ForeignKey('properties.unit_id', ondelete='RESTRICT'), nullable=False)
    owner_id = Column(Integer, ForeignKey('users.user_id', ondelete='RESTRICT'), nullable=False)
    name = Column(String(120), nullable=False)
    revision_of = Column(Integer, ForeignKey('investment_scenarios.scenario_id', ondelete='RESTRICT'), nullable=True)
    formula_version = Column(String(40), nullable=False)
    assumptions = Column(JSONB, nullable=False)
    result = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
