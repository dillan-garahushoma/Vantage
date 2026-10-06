from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.schemas.living_score import LivingScoreResponse
from app.analytics.services.living_score_service import LivingScoreService
from app.db.session import get_db
from app.identity.api.dependencies import CurrentUser
from app.property.schemas.property import (
    PaginatedPropertiesResponse,
    PropertyCreate,
    PropertyResponse,
)
from app.property.services.property_service import PropertyService

router = APIRouter(prefix="/properties", tags=["property"])


@router.get("", response_model=PaginatedPropertiesResponse)
async def search_properties(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    bedrooms: Annotated[int | None, Query(ge=0, description="Exact number of bedrooms")] = None,
    bathrooms: Annotated[int | None, Query(ge=0, description="Exact number of bathrooms")] = None,
    min_size_m2: Annotated[Decimal | None, Query(ge=0, description="Minimum size in m²")] = None,
    max_size_m2: Annotated[Decimal | None, Query(ge=0, description="Maximum size in m²")] = None,
    estate_id: Annotated[int, Query(gt=0)] = ...,
) -> PaginatedPropertiesResponse:
    """List properties, optionally filtered by bedrooms, bathrooms, and size range."""
    return await PropertyService(db).search_properties(
        page=page,
        page_size=page_size,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        min_size_m2=min_size_m2,
        max_size_m2=max_size_m2,
        estate_id=estate_id,
        actor=current_user,
    )


@router.get("/{unit_id}", response_model=PropertyResponse)
async def get_property(
    unit_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    estate_id: Annotated[int, Query(gt=0)],
    current_user: CurrentUser,
) -> PropertyResponse:
    """Fetch a single property by id."""
    return await PropertyService(db).get_property(
        unit_id=unit_id, estate_id=estate_id, actor=current_user
    )


@router.get("/{unit_id}/living-score", response_model=LivingScoreResponse)
async def get_living_score(
    unit_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    estate_id: Annotated[int, Query(gt=0)],
    current_user: CurrentUser,
) -> LivingScoreResponse:
    """Read the legacy property score only inside an authorized estate scope."""
    await PropertyService(db).get_property(
        unit_id=unit_id, estate_id=estate_id, actor=current_user
    )
    return await LivingScoreService(db).get_living_score(unit_id)


@router.post("", response_model=PropertyResponse, status_code=201)
async def create_property(
    payload: PropertyCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
) -> PropertyResponse:
    """Register a new unit/property (HOA admins only)."""
    return await PropertyService(db).create_property(payload, current_user)
