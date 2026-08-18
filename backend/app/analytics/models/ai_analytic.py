from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, Text, TIMESTAMP
from sqlalchemy.sql import func

from app.db.base import Base


class AIAnalytic(Base):
    __tablename__ = "ai_analytics"

    analytics_id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.unit_id", ondelete="SET NULL"), nullable=False)
    predicted_market_value = Column(Numeric(12, 2), nullable=True)
    rental_yield_pct = Column(Numeric(5, 2), nullable=True)
    growth_score = Column(Numeric(5, 2), nullable=True)
    ten_year_roi = Column(Numeric(8, 2), nullable=True)
    calculated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    model_version = Column(String(20), nullable=True)
    confidence_score = Column(Numeric(5, 2), nullable=True)
    actual_market_value = Column(Numeric(12, 2), nullable=True)
    inference_time_ms = Column(Integer, nullable=True)
    input_features_used = Column(Text, nullable=True)
    is_validated = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
