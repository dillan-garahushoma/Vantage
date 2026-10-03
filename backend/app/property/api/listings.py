from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ListingStatus, UserRole
from app.db.session import get_db
from app.identity.api.dependencies import require_roles
from app.identity.models.user import User
from app.property.schemas.listing import (
    ListingCreate,
    ListingResponse,
    ListingUpdate,
    PaginatedListingsResponse,
)
from app.property.services.listing_service import ListingService

router = APIRouter(prefix="/listings", tags=["listings"])

AgentOrAdmin = Annotated[
    User, require_roles(UserRole.estate_agent.value, UserRole.hoa_admin.value)
]


@router.get("", response_model=PaginatedListingsResponse)
async def search_listings(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: Annotated[ListingStatus | None, Query(description="active, sold or withdrawn")] = None,
    unit_id: Annotated[int | None, Query(ge=1)] = None,
    agent_id: Annotated[int | None, Query(ge=1)] = None,
    min_price: Annotated[Decimal | None, Query(ge=0)] = None,
    max_price: Annotated[Decimal | None, Query(ge=0)] = None,
) -> PaginatedListingsResponse:
    """Public listing search, newest first."""
    return await ListingService(db).search_listings(
        page=page,
        page_size=page_size,
        status=status.value if status else None,
        unit_id=unit_id,
        agent_id=agent_id,
        min_price=min_price,
        max_price=max_price,
    )


@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(
    listing_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ListingResponse:
    return await ListingService(db).get_listing(listing_id)


@router.post("", response_model=ListingResponse, status_code=201)
async def create_listing(
    payload: ListingCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: AgentOrAdmin,
) -> ListingResponse:
    """Create a listing. The agent is taken from the logged-in user, not the request body."""
    return await ListingService(db).create_listing(payload, current_user)


@router.patch("/{listing_id}", response_model=ListingResponse)
async def update_listing(
    listing_id: int,
    payload: ListingUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: AgentOrAdmin,
) -> ListingResponse:
    """Edit price, description, photo or status. Agents can only edit their own listings."""
    return await ListingService(db).update_listing(listing_id, payload, current_user)
