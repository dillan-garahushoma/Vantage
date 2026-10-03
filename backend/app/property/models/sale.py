from sqlalchemy import Column, ForeignKey, Integer, Numeric, TIMESTAMP
from sqlalchemy.sql import func

from app.db.base import Base


class Sale(Base):
    __tablename__ = "sales"

    sale_id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("properties.unit_id", ondelete="CASCADE"), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    sale_date = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
