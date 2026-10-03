from sqlalchemy import Column, Integer, Numeric, String, TIMESTAMP
from sqlalchemy.sql import func

from app.db.base import Base


class Property(Base):
    __tablename__ = "properties"

    unit_id = Column(Integer, primary_key=True, index=True)
    unit_no = Column(String(10), nullable=False, unique=True)
    complex_name = Column(String(255), nullable=False)
    street_address = Column(String(255), nullable=False)
    suburb = Column(String(255), nullable=True)
    size_m2 = Column(Numeric(8, 2), nullable=True)
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
