"""
Property domain — ORM entity definitions.
Entities: Estate, Property, Unit.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import PropertyType
from app.db.session import Base


class Estate(Base):
    """A managed residential or mixed-use estate (e.g. a complex or sectional title scheme)."""

    __tablename__ = "estates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    province: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    properties: Mapped[list["Property"]] = relationship("Property", back_populates="estate")

    def __repr__(self) -> str:
        return f"<Estate id={self.id} name={self.name}>"


class Property(Base):
    """A building or property within an estate."""

    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estates.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    erf_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    estate: Mapped["Estate"] = relationship("Estate", back_populates="properties")
    units: Mapped[list["Unit"]] = relationship("Unit", back_populates="property")

    def __repr__(self) -> str:
        return f"<Property id={self.id} name={self.name}>"


class Unit(Base):
    """An individual unit within a property (e.g. flat 4B)."""

    __tablename__ = "units"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    unit_number: Mapped[str] = mapped_column(String(50), nullable=False)
    property_type: Mapped[PropertyType] = mapped_column(
        Enum(PropertyType, name="property_type"), nullable=False
    )
    floor_size_sqm: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    property: Mapped["Property"] = relationship("Property", back_populates="units")

    def __repr__(self) -> str:
        return f"<Unit id={self.id} unit_number={self.unit_number}>"
