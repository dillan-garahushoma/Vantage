"""Estate photographs: upload, list, re-caption, reorder, delete.

Authorization is the estate's, not the caller's: an ``hoa_admin`` membership of
*this* estate is required to write, and any member of it may read the list. The
bytes never touch the database - they are written under ``UPLOAD_DIR`` by
:mod:`app.property.domain.photo_pipeline`, which also guarantees that what lands
on disk is a re-encoded JPEG with no EXIF, no GPS and a random filename.

Failure has to leave nothing behind in either place, so the order is: encode
(everything that can reject the upload happens first), write the files, insert the
row and commit, and if any of that fails, remove the files again. A row is never
committed without its files and files are never left without a row.
"""
from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.core.config import get_settings
from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    PayloadTooLargeException,
)
from app.identity.models.user import User
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.property.domain.photo_pipeline import (
    ALLOWED_CONTENT_TYPES,
    MAX_UPLOAD_BYTES,
    STORED_CONTENT_TYPE,
    encode_photo_pair,
    generate_public_id,
    photo_path,
)
from app.property.models.estate_photo import PHOTO_CAPTION_MAX_LENGTH
from app.property.repositories.estate_photo_repository import EstatePhotoRepository
from app.property.schemas.estate_profile import EstatePhotoResponse, EstatePhotoUpdate

logger = logging.getLogger(__name__)

#: How many photographs one estate may keep. A small, fixed ceiling keeps the
#: public gallery readable and bounds what one administrator can upload.
MAX_PHOTOS_PER_ESTATE = 12

MAX_PHOTOS_MESSAGE = (
    f"This estate already has the maximum of {MAX_PHOTOS_PER_ESTATE} photos. "
    "Delete one before adding another."
)
UNSUPPORTED_TYPE_MESSAGE = "Only JPEG, PNG and WebP images are accepted."
TOO_LARGE_MESSAGE = "That image is larger than the 5 MB limit."


class EstatePhotoService:
    def __init__(self, db: AsyncSession, *, upload_dir: str | Path | None = None) -> None:
        self._db = db
        self._photos = EstatePhotoRepository(db)
        self._authorization = EstateAuthorizationService(db)
        self._upload_dir = Path(
            upload_dir if upload_dir is not None else get_settings().UPLOAD_DIR
        )

    @property
    def upload_dir(self) -> Path:
        return self._upload_dir

    # ---- reads -----------------------------------------------------------

    async def list_photos(self, actor: User, *, estate_id: int) -> list[EstatePhotoResponse]:
        """The estate's photos in display order. Any member of it may read them."""
        await self._authorization.require_membership(actor=actor, estate_id=estate_id)
        rows = await self._photos.list_for_estate(estate_id=estate_id)
        return [EstatePhotoResponse.model_validate(row) for row in rows]

    # ---- writes ----------------------------------------------------------

    async def _require_estate_admin(self, actor: User, estate_id: int) -> None:
        await self._authorization.require_role(
            actor=actor,
            estate_id=estate_id,
            allowed_roles=(UserRole.hoa_admin.value,),
        )

    async def upload_photo(
        self,
        actor: User,
        *,
        estate_id: int,
        filename: str | None,
        content_type: str | None,
        data: bytes,
        caption: str | None = None,
    ) -> EstatePhotoResponse:
        """Validate, re-encode and store one photograph, then record its row.

        ``filename`` is accepted only so the caller can pass what the client sent;
        it is never used for anything. The stored name comes from
        :func:`generate_public_id`.
        """
        await self._require_estate_admin(actor, estate_id)

        if await self._photos.count_for_estate(estate_id=estate_id) >= MAX_PHOTOS_PER_ESTATE:
            raise ConflictException(MAX_PHOTOS_MESSAGE)
        if content_type is not None and content_type not in ALLOWED_CONTENT_TYPES:
            raise BadRequestException(UNSUPPORTED_TYPE_MESSAGE)
        if len(data) > MAX_UPLOAD_BYTES:
            raise PayloadTooLargeException(TOO_LARGE_MESSAGE)

        # Everything that can reject the upload happens before a byte is written.
        full_bytes, thumb_bytes, width, height = encode_photo_pair(data)

        public_id = generate_public_id()
        full_path = photo_path(self._upload_dir, public_id)
        thumb_extra_path = photo_path(self._upload_dir, public_id, thumb=True)

        clean_caption = (caption or "").strip()[:PHOTO_CAPTION_MAX_LENGTH] or None
        position = await self._photos.next_position(estate_id=estate_id)

        self._write_files(full_path, thumb_extra_path, full_bytes, thumb_bytes)
        try:
            photo = await self._photos.add(
                estate_id=estate_id,
                public_id=public_id,
                content_type=STORED_CONTENT_TYPE,
                width=width,
                height=height,
                bytes=len(full_bytes),
                caption=clean_caption,
                position=position,
                uploaded_by=actor.user_id,
            )
            await self._db.commit()
            await self._db.refresh(photo)
        except Exception:
            await self._db.rollback()
            self._remove_files(full_path, thumb_extra_path)
            raise

        logger.info(
            "estate photo stored (estate_id=%s photo_id=%s bytes=%s)",
            estate_id,
            photo.photo_id,
            photo.bytes,
        )
        return EstatePhotoResponse.model_validate(photo)

    async def update_photo(
        self,
        actor: User,
        *,
        estate_id: int,
        photo_id: int,
        payload: EstatePhotoUpdate,
    ) -> EstatePhotoResponse:
        """Re-caption or reorder one photo. The image itself is never replaced."""
        await self._require_estate_admin(actor, estate_id)
        photo = await self._photos.get_by_id_in_estate(photo_id=photo_id, estate_id=estate_id)
        if photo is None:
            raise NotFoundException(f"Photo with id {photo_id} was not found.")

        changes = payload.model_dump(exclude_unset=True)
        if "caption" in changes:
            caption = changes["caption"]
            changes["caption"] = (
                caption.strip()[:PHOTO_CAPTION_MAX_LENGTH] if caption else None
            )
        for field, value in changes.items():
            setattr(photo, field, value)
        photo = await self._photos.save(photo)
        await self._db.commit()
        await self._db.refresh(photo)
        return EstatePhotoResponse.model_validate(photo)

    async def delete_photo(self, actor: User, *, estate_id: int, photo_id: int) -> None:
        """Remove one photo's row and its files."""
        await self._require_estate_admin(actor, estate_id)
        photo = await self._photos.get_by_id_in_estate(photo_id=photo_id, estate_id=estate_id)
        if photo is None:
            raise NotFoundException(f"Photo with id {photo_id} was not found.")

        public_id = photo.public_id
        await self._photos.delete(photo)
        await self._db.commit()
        self._remove_files(
            photo_path(self._upload_dir, public_id),
            photo_path(self._upload_dir, public_id, thumb=True),
        )

    # ---- file I/O --------------------------------------------------------

    def _write_files(
        self, full_path: Path, thumb_path: Path, full_bytes: bytes, thumb_bytes: bytes
    ) -> None:
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(full_bytes)
        thumb_path.write_bytes(thumb_bytes)

    def _remove_files(self, *paths: Path) -> None:
        """Best-effort removal: a missing file is not an error worth failing on."""
        for path in paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:  # pragma: no cover - permission/lock issues
                logger.warning("could not remove photo file %s", path.name)


__all__ = ["EstatePhotoService", "MAX_PHOTOS_PER_ESTATE", "MAX_PHOTOS_MESSAGE"]
