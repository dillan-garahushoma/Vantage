"""
Analytics domain — ORM entity definitions.
Entities: LivingScore, PropertyValuationSnapshot.

Analytics is VALORA's core differentiator. This domain will grow to own
prediction_service, living_score_service, and roi_service.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, SmallInteger, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class LivingScore(Base):
    """
    Computed living quality score for an estate at a point in time.

    Score: 0–100 (100 = perfect living conditions).
    Sub-scores break down the overall score by dimension.
    """

    __tablename__ = "living_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estates.id", ondelete="CASCADE"), nullable=False
    )
    overall_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    maintenance_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    community_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    safety_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    amenity_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<LivingScore estate_id={self.estate_id} overall={self.overall_score}>"


class PropertyValuationSnapshot(Base):
    """
    Point-in-time property valuation estimate for a unit.

    Snapshots are created by the analytics engine after each Living Score run
    or when a valuation adjustment event occurs.
    """

    __tablename__ = "property_valuation_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id", ondelete="CASCADE"), nullable=False
    )
    estimated_value: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    living_score_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("living_scores.id", ondelete="SET NULL"), nullable=True
    )
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)  # 0.0–1.0
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"<PropertyValuationSnapshot unit_id={self.unit_id}"
            f" value={self.estimated_value}>"
        )
