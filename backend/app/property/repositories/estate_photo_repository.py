"""Queries and persistence for estate photos. Metadata only - no file I/O here.

The bytes are the service's business (``EstatePhotoService`` owns the directory);
this repository only ever sees rows. Every lookup is estate-scoped, so a photo id
from another estate resolves to ``None`` and becomes a 404 rather than a 403.
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.property.models.estate_photo import EstatePhoto


class EstatePhotoRepository:
    """Rows only: the bytes live under ``UPLOAD_DIR`` and belong to the service."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @staticmethod
    def _ordered(stmt):
        """Lowest position first, with the id as a stable tie-break."""
        return stmt.order_by(EstatePhoto.position.asc(), EstatePhoto.photo_id.asc())

    async def list_for_estate(self, *, estate_id: int) -> list[EstatePhoto]:
        result = await self._db.execute(
            self._ordered(
                select(EstatePhoto).where(EstatePhoto.estate_id == estate_id)
            )
        )
        return list(result.scalars().all())

    async def list_for_estates(self, *, estate_ids: list[int]) -> list[EstatePhoto]:
        """Every photo of several estates at once, in display order.

        Used by the public grid to pick one cover per estate in a single query
        rather than one query per estate.
        """
        if not estate_ids:
            return []
        result = await self._db.execute(
            self._ordered(
                select(EstatePhoto).where(EstatePhoto.estate_id.in_(estate_ids))
            )
        )
        return list(result.scalars().all())

    async def count_for_estate(self, *, estate_id: int) -> int:
        result = await self._db.execute(
            select(func.count())
            .select_from(EstatePhoto)
            .where(EstatePhoto.estate_id == estate_id)
        )
        return int(result.scalar_one())

    async def get_by_id_in_estate(
        self, *, photo_id: int, estate_id: int
    ) -> EstatePhoto | None:
        result = await self._db.execute(
            select(EstatePhoto).where(
                EstatePhoto.photo_id == photo_id,
                EstatePhoto.estate_id == estate_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_public_id(self, public_id: str) -> EstatePhoto | None:
        """The public endpoint's only lookup: by the unguessable handle."""
        result = await self._db.execute(
            select(EstatePhoto).where(EstatePhoto.public_id == public_id)
        )
        return result.scalar_one_or_none()

    async def next_position(self, *, estate_id: int) -> int:
        """Append after the last photo (``count`` is the next free position)."""
        return await self.count_for_estate(estate_id=estate_id)

    async def add(self, **fields: object) -> EstatePhoto:
        """Add a row without committing; the service commits once."""
        photo = EstatePhoto(**fields)
        self._db.add(photo)
        await self._db.flush()
        return photo

    async def save(self, photo: EstatePhoto) -> EstatePhoto:
        """Persist field changes without committing; the service commits once."""
        await self._db.flush()
        await self._db.refresh(photo)
        return photo

    async def delete(self, photo: EstatePhoto) -> None:
        """Remove the row without committing; the service commits once."""
        await self._db.delete(photo)
        await self._db.flush()
