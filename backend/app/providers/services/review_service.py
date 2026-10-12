from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.core.exceptions import ConflictException, NotFoundException
from app.identity.models.user import User
from app.identity.repositories.estate_membership_repository import EstateMembershipRepository
from app.providers.repositories.review_repository import ReviewRepository
from app.providers.repositories.service_provider_repository import ServiceProviderRepository
from app.providers.schemas.review import PaginatedReviewsResponse, ReviewCreate, ReviewResponse


class ReviewService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repo = ReviewRepository(db)
        self._provider_repo = ServiceProviderRepository(db)
        self._memberships = EstateMembershipRepository(db)

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
        # A resident may only review a provider who actually works in an estate the
        # resident is a member of. Anything else is the same 404 as an unknown
        # provider, so this endpoint cannot be used to probe the directory.
        if not await self._works_in_a_shared_estate(
            resident_user_id=user.user_id, provider=provider
        ):
            raise NotFoundException(
                f"Service provider with id {provider_id} was not found."
            )
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

    async def _works_in_a_shared_estate(self, *, resident_user_id: int, provider) -> bool:
        """True when the resident and the provider hold memberships in the same estate."""
        if provider.user_id is None:
            # A legacy provider row with no account cannot be a member anywhere.
            return False
        resident_estates = set(
            await self._memberships.list_estate_ids(user_id=resident_user_id)
        )
        if not resident_estates:
            return False
        provider_estates = set(
            await self._memberships.list_estate_ids(
                user_id=provider.user_id,
                membership_role=UserRole.service_provider.value,
            )
        )
        return bool(resident_estates & provider_estates)

    async def _get_provider_or_404(self, provider_id: int):
        provider = await self._provider_repo.get_by_id(provider_id)
        if provider is None:
            raise NotFoundException(f"Service provider with id {provider_id} was not found.")
        return provider
