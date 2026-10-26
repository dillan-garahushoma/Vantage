from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
    text,
)
from sqlalchemy.sql import func

from app.db.base import Base


class Property(Base):
    """One residential unit within an estate (the complex/tenant boundary)."""

    __tablename__ = "properties"
    __table_args__ = (
        UniqueConstraint("estate_id", "unit_no", name="uq_properties_estate_unit_no"),
        CheckConstraint(
            "availability_status IN ('available', 'occupied', 'not_available')",
            name="ck_properties_availability_status",
        ),
        Index(
            "uq_properties_legacy_unit_no",
            "unit_no",
            unique=True,
            postgresql_where=text("estate_id IS NULL"),
        ),
        Index(
            "ix_properties_public_units",
            "estate_id",
            "is_public_listing",
            "availability_status",
        ),
    )

    unit_id = Column(Integer, primary_key=True, index=True)
    # Nullable only for legacy records that predate estate tenancy.
    estate_id = Column(
        Integer, ForeignKey("estates.estate_id", ondelete="RESTRICT"), nullable=True
    )
    unit_no = Column(String(10), nullable=False)
    complex_name = Column(String(255), nullable=False)
    street_address = Column(String(255), nullable=False)
    suburb = Column(String(255), nullable=True)
    size_m2 = Column(Numeric(8, 2), nullable=True)
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Integer, nullable=True)

    # Public-facing details are an explicit HOA-controlled showcase. The internal
    # unit number/address and occupancy records are never included in public DTOs.
    listing_title = Column(String(160), nullable=True)
    listing_description = Column(Text, nullable=True)
    amenities = Column(JSON, nullable=False, default=list, server_default=text("'[]'"))
    is_public_listing = Column(Boolean, nullable=False, server_default=text("false"))
    # Random public reference used only when a unit is published; never the unit number.
    public_listing_id = Column(String(32), nullable=True, unique=True)
    availability_status = Column(
        String(20), nullable=False, server_default=text("'not_available'")
    )

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
