from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.property.models.property_photo import PropertyPhoto


class PropertyPhotoRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_for_property(self, *, property_id: int) -> list[PropertyPhoto]:
        result = await self._db.execute(
            select(PropertyPhoto)
            .where(PropertyPhoto.property_id == property_id)
            .order_by(PropertyPhoto.position.asc(), PropertyPhoto.photo_id.asc())
        )
        return list(result.scalars().all())

    async def list_for_properties(self, *, property_ids: list[int]) -> list[PropertyPhoto]:
        if not property_ids:
            return []
        result = await self._db.execute(
            select(PropertyPhoto)
            .where(PropertyPhoto.property_id.in_(property_ids))
            .order_by(PropertyPhoto.position.asc(), PropertyPhoto.photo_id.asc())
        )
        return list(result.scalars().all())

    async def get_by_public_id(self, public_id: str) -> PropertyPhoto | None:
        result = await self._db.execute(
            select(PropertyPhoto).where(PropertyPhoto.public_id == public_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_in_property(self, *, photo_id: int, property_id: int) -> PropertyPhoto | None:
        result = await self._db.execute(
            select(PropertyPhoto).where(
                PropertyPhoto.photo_id == photo_id,
                PropertyPhoto.property_id == property_id,
            )
        )
        return result.scalar_one_or_none()

    async def count_for_property(self, *, property_id: int) -> int:
        from sqlalchemy import func
        result = await self._db.execute(
            select(func.count()).select_from(PropertyPhoto).where(PropertyPhoto.property_id == property_id)
        )
        return int(result.scalar_one())

    async def add(self, **fields: object) -> PropertyPhoto:
        photo = PropertyPhoto(**fields)
        self._db.add(photo)
        await self._db.flush()
        return photo

    async def delete(self, photo: PropertyPhoto) -> None:
        await self._db.delete(photo)
        await self._db.flush()
