from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text, TIMESTAMP
from sqlalchemy.sql import func

from app.db.base import Base


class Listing(Base):
    __tablename__ = "listings"

    listing_id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, nullable=False)
    agent_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    description = Column(Text, nullable=True)
    photo_url = Column(Text, nullable=True)
    status = Column(String(20), default="active")
    views = Column(Integer, default=0)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
