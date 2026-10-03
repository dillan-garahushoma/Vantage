from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.identity.models.user import User
from app.providers.repositories.review_repository import ReviewRepository
from app.providers.repositories.service_provider_repository import ServiceProviderRepository
from app.providers.schemas.review import PaginatedReviewsResponse, ReviewCreate, ReviewResponse


class ReviewService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repo = ReviewRepository(db)
        self._provider_repo = ServiceProviderRepository(db)

    async def list_reviews(self, provider_id: int) -> PaginatedReviewsResponse:
        await self._get_provider_or_404(provider_id)
        reviews = await self._repo.list_for_provider(provider_id)
        return PaginatedReviewsResponse(
            count=len(reviews),
            reviews=[ReviewResponse.model_validate(r) for r in reviews],
        )

    async def create_review(
        self, provider_id: int, payload: ReviewCreate, user: User
    ) -> ReviewResponse:
        provider = await self._get_provider_or_404(provider_id)
        if await self._repo.get_by_user_and_provider(user.user_id, provider_id) is not None:
            raise ConflictException("You have already reviewed this service provider.")

        comment = payload.comment.strip() if payload.comment else None
        review = await self._repo.add(
            user_id=user.user_id,
            provider_id=provider_id,
            rating=payload.rating,
            comment=comment or None,
        )

        # keep the provider's cached rating in step with its reviews (same transaction)
        avg, count = await self._repo.rating_summary(provider_id)
        provider.total_reviews = count
        provider.avg_rating = (
            avg.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if avg is not None else None
        )

        await self._db.commit()
        await self._db.refresh(review)
        return ReviewResponse.model_validate(review)

    async def _get_provider_or_404(self, provider_id: int):
        provider = await self._provider_repo.get_by_id(provider_id)
        if provider is None:
            raise NotFoundException(f"Service provider with id {provider_id} was not found.")
        return provider
