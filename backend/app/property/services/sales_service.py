from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.core.exceptions import ForbiddenException, NotFoundException
from app.identity.models.user import User
from app.property.models.listing import Listing
from app.property.repositories.listing_repository import ListingRepository
from app.property.repositories.property_repository import PropertyRepository
from app.property.schemas.listing import (
    ListingCreate,
    ListingResponse,
    ListingUpdate,
    PaginatedListingsResponse,
)


class ListingService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = ListingRepository(db)
        self._property_repo = PropertyRepository(db)

    async def search_listings(
        self,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
        unit_id: int | None = None,
        agent_id: int | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
    ) -> PaginatedListingsResponse:
        filters = dict(
            status=status,
            unit_id=unit_id,
            agent_id=agent_id,
            min_price=min_price,
            max_price=max_price,
        )
        listings = await self._repo.search(offset=(page - 1) * page_size, limit=page_size, **filters)
        total = await self._repo.count(**filters)
        return PaginatedListingsResponse(
            count=total,
            page=page,
            page_size=page_size,
            listings=[ListingResponse.model_validate(item) for item in listings],
        )

    async def get_listing(self, listing_id: int) -> ListingResponse:
        return ListingResponse.model_validate(await self._get_or_404(listing_id))

    async def create_listing(self, payload: ListingCreate, agent: User) -> ListingResponse:
        if await self._property_repo.get_by_id(payload.unit_id) is None:
            raise NotFoundException(f"Property with id {payload.unit_id} was not found.")
        listing = await self._repo.create(
            unit_id=payload.unit_id,
            agent_id=agent.user_id,
            price=payload.price,
            description=payload.description,
            photo_url=payload.photo_url,
        )
        return ListingResponse.model_validate(listing)

    async def update_listing(
        self, listing_id: int, payload: ListingUpdate, actor: User
    ) -> ListingResponse:
        listing = await self._get_or_404(listing_id)
        if actor.role != UserRole.hoa_admin.value and listing.agent_id != actor.user_id:
            raise ForbiddenException("You can only edit your own listings.")

        changes = payload.model_dump(exclude_unset=True)
        # price and status are NOT NULL in the database, so ignore explicit nulls for them
        for required_field in ("price", "status"):
            if required_field in changes and changes[required_field] is None:
                del changes[required_field]
        if "status" in changes:
            changes["status"] = changes["status"].value

        listing = await self._repo.update(listing, changes)
        return ListingResponse.model_validate(listing)

    async def _get_or_404(self, listing_id: int) -> Listing:
        listing = await self._repo.get_by_id(listing_id)
        if listing is None:
            raise NotFoundException(f"Listing with id {listing_id} was not found.")
        return listing
