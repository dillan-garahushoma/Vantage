"""Secure upload lifecycle for photographs attached to one residential unit."""
from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.core.config import get_settings
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException, PayloadTooLargeException
from app.identity.models.user import User
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.property.domain.photo_pipeline import (
    ALLOWED_CONTENT_TYPES, MAX_UPLOAD_BYTES, STORED_CONTENT_TYPE,
    encode_photo_pair, generate_public_id, photo_path,
)
from app.property.repositories.property_photo_repository import PropertyPhotoRepository
from app.property.repositories.property_repository import PropertyRepository

logger = logging.getLogger(__name__)
MAX_PHOTOS_PER_UNIT = 8


class PropertyPhotoService:
    def __init__(self, db: AsyncSession, *, upload_dir: str | Path | None = None) -> None:
        self._db = db
        self._photos = PropertyPhotoRepository(db)
        self._properties = PropertyRepository(db)
        self._authorization = EstateAuthorizationService(db)
        self._upload_dir = Path(upload_dir if upload_dir is not None else get_settings().UPLOAD_DIR)

    async def list_photos(self, *, property_id: int, estate_id: int, actor: User) -> list[dict]:
        await self._authorization.require_membership(actor=actor, estate_id=estate_id)
        unit = await self._properties.get_by_id_in_estate(unit_id=property_id, estate_id=estate_id)
        if unit is None:
            raise NotFoundException(f"Unit {property_id} was not found.")
        return [self._dto(photo) for photo in await self._photos.list_for_property(property_id=property_id)]

    async def upload_photo(
        self, *, property_id: int, estate_id: int, actor: User,
        filename: str | None, content_type: str | None, data: bytes, caption: str | None = None,
    ) -> dict:
        await self._authorization.require_role(
            actor=actor, estate_id=estate_id, allowed_roles=(UserRole.hoa_admin.value,)
        )
        unit = await self._properties.get_by_id_in_estate(unit_id=property_id, estate_id=estate_id)
        if unit is None:
            raise NotFoundException(f"Unit {property_id} was not found.")
        if await self._photos.count_for_property(property_id=property_id) >= MAX_PHOTOS_PER_UNIT:
            raise ConflictException(f"This unit already has the maximum of {MAX_PHOTOS_PER_UNIT} photos.")
        if content_type is not None and content_type not in ALLOWED_CONTENT_TYPES:
            raise BadRequestException("Only JPEG, PNG and WebP images are accepted.")
        if len(data) > MAX_UPLOAD_BYTES:
            raise PayloadTooLargeException("That image is larger than the 5 MB limit.")
        full_bytes, thumb_bytes, width, height = encode_photo_pair(data)
        public_id = generate_public_id()
        full_path = photo_path(self._upload_dir, public_id)
        thumb_path = photo_path(self._upload_dir, public_id, thumb=True)
        clean_caption = (caption or "").strip()[:140] or None
        position = await self._photos.count_for_property(property_id=property_id)
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        try:
            full_path.write_bytes(full_bytes)
            thumb_path.write_bytes(thumb_bytes)
            photo = await self._photos.add(
                property_id=property_id, public_id=public_id, content_type=STORED_CONTENT_TYPE,
                width=width, height=height, bytes=len(full_bytes), caption=clean_caption,
                position=position, uploaded_by=actor.user_id,
            )
            await self._db.commit()
            await self._db.refresh(photo)
        except Exception:
            await self._db.rollback()
            full_path.unlink(missing_ok=True)
            thumb_path.unlink(missing_ok=True)
            raise
        logger.info("unit photo stored (estate_id=%s property_id=%s photo_id=%s)", estate_id, property_id, photo.photo_id)
        return self._dto(photo)

    async def read_photo(self, *, property_id: int, photo_id: int, estate_id: int, actor: User, size: str = "full") -> tuple[bytes, str]:
        """Serve a unit photo only to a member of the estate that owns the unit."""
        await self._authorization.require_membership(actor=actor, estate_id=estate_id)
        unit = await self._properties.get_by_id_in_estate(unit_id=property_id, estate_id=estate_id)
        if unit is None:
            raise NotFoundException(f"Unit {property_id} was not found.")
        photo = await self._photos.get_by_id_in_property(photo_id=photo_id, property_id=property_id)
        if photo is None:
            raise NotFoundException(f"Photo {photo_id} was not found.")
        path = photo_path(self._upload_dir, photo.public_id, thumb=size == "thumb")
        if not path.is_file():
            raise NotFoundException("That unit photograph is not available.")
        return path.read_bytes(), photo.content_type

    async def delete_photo(self, *, property_id: int, photo_id: int, estate_id: int, actor: User) -> None:
        await self._authorization.require_role(
            actor=actor, estate_id=estate_id, allowed_roles=(UserRole.hoa_admin.value,)
        )
        unit = await self._properties.get_by_id_in_estate(unit_id=property_id, estate_id=estate_id)
        if unit is None:
            raise NotFoundException(f"Unit {property_id} was not found.")
        photo = await self._photos.get_by_id_in_property(photo_id=photo_id, property_id=property_id)
        if photo is None:
            raise NotFoundException(f"Photo {photo_id} was not found.")
        public_id = photo.public_id
        await self._photos.delete(photo)
        await self._db.commit()
        for path in (photo_path(self._upload_dir, public_id), photo_path(self._upload_dir, public_id, thumb=True)):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.warning("could not remove unit photo file %s", path.name)

    @staticmethod
    def _dto(photo) -> dict:
        return {
            "photo_id": photo.photo_id, "public_id": photo.public_id,
            "content_type": photo.content_type, "width": photo.width, "height": photo.height,
            "bytes": photo.bytes, "caption": photo.caption, "position": photo.position,
        }
