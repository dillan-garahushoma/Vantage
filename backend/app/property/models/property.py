from sqlalchemy import Column, ForeignKey, Index, Integer, Numeric, String, TIMESTAMP, UniqueConstraint, text
from sqlalchemy.sql import func

from app.db.base import Base


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (
        UniqueConstraint("estate_id", "unit_no", name="uq_properties_estate_unit_no"),
        Index(
            "uq_properties_legacy_unit_no",
            "unit_no",
            unique=True,
            postgresql_where=text("estate_id IS NULL"),
        ),
    )

    unit_id = Column(Integer, primary_key=True, index=True)
    # Nullable only for legacy records that predate estate tenancy. New operational data
    # must be associated through an explicit estate and membership relationship.
    estate_id = Column(Integer, ForeignKey("estates.estate_id", ondelete="RESTRICT"), nullable=True)
    unit_no = Column(String(10), nullable=False)
    complex_name = Column(String(255), nullable=False)
    street_address = Column(String(255), nullable=False)
    suburb = Column(String(255), nullable=True)
    size_m2 = Column(Numeric(8, 2), nullable=True)
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
