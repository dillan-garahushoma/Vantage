"""Metadata for public unit-listing photographs; bytes live under UPLOAD_DIR."""
from sqlalchemy import (
    CheckConstraint, Column, ForeignKey, Index, Integer, String, TIMESTAMP
)
from sqlalchemy.sql import func

from app.db.base import Base

UNIT_PHOTO_PUBLIC_ID_LENGTH = 32
UNIT_PHOTO_CAPTION_MAX_LENGTH = 140


class PropertyPhoto(Base):
    __tablename__ = "property_photos"
    __table_args__ = (
        CheckConstraint("width > 0 AND height > 0 AND bytes > 0", name="ck_property_photos_dimensions_positive"),
        Index("ix_property_photos_property_id_position", "property_id", "position"),
    )

    photo_id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.unit_id", ondelete="CASCADE"), nullable=False)
    public_id = Column(String(UNIT_PHOTO_PUBLIC_ID_LENGTH), nullable=False, unique=True)
    content_type = Column(String(32), nullable=False, server_default="image/jpeg")
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    bytes = Column(Integer, nullable=False)
    caption = Column(String(UNIT_PHOTO_CAPTION_MAX_LENGTH), nullable=True)
    position = Column(Integer, nullable=False, server_default="0")
    uploaded_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
