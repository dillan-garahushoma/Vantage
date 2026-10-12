"""The estate's photographs: metadata only, bytes live on disk.

One row is one photograph of one estate. The bytes are **never** stored in the
database: they live under ``UPLOAD_DIR`` as ``<public_id>.jpg`` (full, at most
1920 px on the longest side) and ``<public_id>_thumb.jpg`` (480 px), both
re-encoded by ``EstatePhotoService`` from the upload, so the original filename,
the EXIF block and any GPS coordinates are gone before anything is written.

``public_id`` is the only handle the public endpoint accepts. It is 32 random
characters, unique for all time, so photos cannot be enumerated and a deleted
photo's URL cannot be reissued to a different picture.

``uploaded_by`` is ``ON DELETE SET NULL``: removing the administrator who uploaded
a photo must not delete the estate's photos. ``estate_id`` is ``RESTRICT`` so an
estate cannot be removed from under its photos by accident.
"""
from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    TIMESTAMP,
)
from sqlalchemy.sql import func

from app.db.base import Base

PHOTO_PUBLIC_ID_LENGTH = 32
PHOTO_CAPTION_MAX_LENGTH = 140


class EstatePhoto(Base):
    __tablename__ = "estate_photos"
    __table_args__ = (
        CheckConstraint(
            "width > 0 AND height > 0 AND bytes > 0",
            name="ck_estate_photos_dimensions_positive",
        ),
        Index("ix_estate_photos_estate_id_position", "estate_id", "position"),
    )

    photo_id = Column(Integer, primary_key=True, index=True)
    estate_id = Column(
        Integer,
        ForeignKey("estates.estate_id", ondelete="RESTRICT"),
        nullable=False,
    )
    # The unguessable, stable public handle. Never reused, never guessable.
    public_id = Column(String(PHOTO_PUBLIC_ID_LENGTH), nullable=False, unique=True)
    # What was stored (always image/jpeg today - every upload is re-encoded).
    content_type = Column(String(32), nullable=False, server_default="image/jpeg")
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    bytes = Column(Integer, nullable=False)
    caption = Column(String(PHOTO_CAPTION_MAX_LENGTH), nullable=True)
    # Display order, lowest first. The lowest position is the estate's cover photo.
    position = Column(Integer, nullable=False, server_default="0")
    uploaded_by = Column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
