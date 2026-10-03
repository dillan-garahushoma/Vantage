from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.models.review import Review


class ReviewRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_for_provider(self, provider_id: int) -> list[Review]:
        result = await self._db.execute(
            select(Review)
            .where(Review.provider_id == provider_id)
            .order_by(Review.created_at.desc(), Review.review_id.desc())
        )
        return list(result.scalars().all())

    async def get_by_user_and_provider(self, user_id: int, provider_id: int) -> Review | None:
        result = await self._db.execute(
            select(Review).where(Review.user_id == user_id, Review.provider_id == provider_id)
        )
        return result.scalar_one_or_none()

    async def add(
        self, *, user_id: int, provider_id: int, rating: int, comment: str | None
    ) -> Review:
        """Add a review and flush it (no commit) so the caller can update provider stats atomically."""
        review = Review(user_id=user_id, provider_id=provider_id, rating=rating, comment=comment)
        self._db.add(review)
        await self._db.flush()
        return review

    async def rating_summary(self, provider_id: int) -> tuple[Decimal | None, int]:
        result = await self._db.execute(
            select(func.avg(Review.rating), func.count(Review.review_id)).where(
                Review.provider_id == provider_id
            )
        )
        avg, count = result.one()
        return (Decimal(str(avg)) if avg is not None else None, int(count))
