from sqlalchemy import Column, Integer, String, Text, TIMESTAMP
from sqlalchemy.sql import func

from app.db.base import Base


class Estate(Base):
    """The tenant and operational-health boundary for VALORA data."""

    __tablename__ = "estates"

    estate_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(160), nullable=False, unique=True)
    suburb = Column(String(120), nullable=False)
    city = Column(String(120), nullable=False)
    province = Column(String(80), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
