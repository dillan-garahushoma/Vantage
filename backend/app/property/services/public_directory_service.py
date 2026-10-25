"""The public directory: what an anonymous visitor may see, and nothing else.

This is the only service in VALORA that deliberately runs with **no actor**. That
is why it is written the way it is:

* every directory query is filtered by ``is_public`` in SQL
  (``EstateRepository.public_statement``), so an unpublished estate cannot be
  returned even by a bug in the mapping layer. ``is_demo`` tracks score-data
  origin; seeded demo fixtures stay private by setting ``is_public = false``;
* the DTOs live in :mod:`app.property.schemas.public_directory` and are an
  allow-list, so a new column cannot leak into a public response by accident;
* the Living Score is published only when the estate set ``show_living_score``
  **and** a snapshot exists, and only as the four-field summary - never the
  per-component breakdown, the drivers or the raw inputs;
* a photo is served by its 32-character random ``public_id``. **Open question
  (recorded, not fixed):** that handle is served regardless of ``is_public``, so a
  photo whose estate is later unpublished, or a photo that was never in a
  published album, is still readable by anyone holding its id. The id is
  unguessable and photos are estate-approved images, but the rule is "unlisted,
  not private", and that is a product decision to revisit.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.repositories.living_score_snapshot_repository import (
    LivingScoreSnapshotRepository,
)
from app.core.config import get_settings
from app.core.exceptions import NotFoundException
from app.property.domain.photo_pipeline import STORED_CONTENT_TYPE, photo_path
from app.property.models.estate import Estate
from app.property.repositories.estate_photo_repository import EstatePhotoRepository
from app.property.repositories.estate_repository import EstateRepository
from app.property.repositories.property_repository import PropertyRepository
from app.property.schemas.public_directory import (
    PublicEstateDetailResponse,
    PublicEstateListItem,
    PublicLivingScoreSummary,
    PublicPhotoResponse,
)

NOT_PUBLIC_MESSAGE = "That estate is not available."
PHOTO_NOT_FOUND_MESSAGE = "That photo is not available."


class PublicDirectoryService:
    def __init__(self, db: AsyncSession, *, upload_dir: str | Path | None = None) -> None:
        self._estates = EstateRepository(db)
        self._photos = EstatePhotoRepository(db)
        self._properties = PropertyRepository(db)
        self._snapshots = LivingScoreSnapshotRepository(db)
        self._upload_dir = Path(
            upload_dir if upload_dir is not None else get_settings().UPLOAD_DIR
        )

    async def list_estates(
        self, *, page: int, page_size: int, q: str | None = None
    ) -> tuple[list[PublicEstateListItem], int]:
        """One page of published estates, with unit counts and cover photos."""
        estates = await self._estates.list_public(
            offset=(page - 1) * page_size, limit=page_size, q=q
        )
        total = await self._estates.count_public(q=q)
        if not estates:
            return [], total

        estate_ids = [estate.estate_id for estate in estates]
        unit_counts = await self._properties.counts_for_estates(estate_ids=estate_ids)
        covers: dict[int, str] = {}
        for photo in await self._photos.list_for_estates(estate_ids=estate_ids):
            # First row per estate in display order wins.
            covers.setdefault(photo.estate_id, photo.public_id)

        return (
            [
                self._to_list_item(
                    estate,
                    unit_count=unit_counts.get(estate.estate_id, 0),
                    cover_photo_public_id=covers.get(estate.estate_id),
                )
                for estate in estates
            ],
            total,
        )

    async def get_estate(self, estate_id: int) -> PublicEstateDetailResponse:
        """One published estate: its photos and, if it opted in, its score."""
        estate = await self._estates.get_by_id(estate_id)
        # A private estate and an unknown estate are the same 404: the directory
        # never confirms that a private estate exists.
        if estate is None or not estate.is_public:
            raise NotFoundException(NOT_PUBLIC_MESSAGE)

        photos = await self._photos.list_for_estate(estate_id=estate_id)
        unit_count = await self._properties.count(estate_id=estate_id)
        return PublicEstateDetailResponse(
            estate_id=estate.estate_id,
            name=estate.name,
            suburb=estate.suburb,
            city=estate.city,
            province=estate.province,
            description=estate.description,
            unit_count=unit_count,
            photos=[
                PublicPhotoResponse(public_id=photo.public_id, caption=photo.caption)
                for photo in photos
            ],
            living_score=await self._living_score_summary(estate),
        )

    async def read_photo(self, public_id: str, *, size: str) -> tuple[bytes, str]:
        """The stored bytes of one photo, by its public handle."""
        photo = await self._photos.get_by_public_id(public_id)
        if photo is None:
            raise NotFoundException(PHOTO_NOT_FOUND_MESSAGE)
        path = photo_path(self._upload_dir, public_id, thumb=size == "thumb")
        if not path.is_file():
            # A row whose file is missing is not served as a broken image.
            raise NotFoundException(PHOTO_NOT_FOUND_MESSAGE)
        return path.read_bytes(), photo.content_type or STORED_CONTENT_TYPE

    async def _living_score_summary(self, estate: Estate) -> PublicLivingScoreSummary | None:
        """The score summary, only when published and only when one exists."""
        if not estate.show_living_score:
            return None
        snapshot = await self._snapshots.latest_for_estate(estate_id=estate.estate_id)
        if snapshot is None:
            return None
        return PublicLivingScoreSummary(
            overall_score=snapshot.overall_score,
            status=snapshot.status,
            as_of=snapshot.as_of,
            engine_version=snapshot.engine_version,
            data_origin="demo" if estate.is_demo else "live",
        )

    @staticmethod
    def _to_list_item(
        estate: Estate, *, unit_count: int, cover_photo_public_id: str | None
    ) -> PublicEstateListItem:
        return PublicEstateListItem(
            estate_id=estate.estate_id,
            name=estate.name,
            suburb=estate.suburb,
            city=estate.city,
            province=estate.province,
            description=estate.description,
            unit_count=unit_count,
            cover_photo_public_id=cover_photo_public_id,
        )
