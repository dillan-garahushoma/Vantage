from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.schemas.living_score import LivingScoreResponse
from app.analytics.services.living_score_service import LivingScoreService
from app.common.enums import UserRole
from app.db.session import get_db
from app.identity.api.dependencies import require_roles
from app.identity.models.user import User
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
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    bedrooms: Annotated[int | None, Query(ge=0, description="Exact number of bedrooms")] = None,
    bathrooms: Annotated[int | None, Query(ge=0, description="Exact number of bathrooms")] = None,
    min_size_m2: Annotated[Decimal | None, Query(ge=0, description="Minimum size in m²")] = None,
    max_size_m2: Annotated[Decimal | None, Query(ge=0, description="Maximum size in m²")] = None,
) -> PaginatedPropertiesResponse:
    """List properties, optionally filtered by bedrooms, bathrooms, and size range."""
    return await PropertyService(db).search_properties(
        page=page,
        page_size=page_size,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        min_size_m2=min_size_m2,
        max_size_m2=max_size_m2,
    )


@router.get("/{unit_id}", response_model=PropertyResponse)
async def get_property(
    unit_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PropertyResponse:
    """Fetch a single property by id."""
    return await PropertyService(db).get_property(unit_id)


@router.get("/{unit_id}/living-score", response_model=LivingScoreResponse)
async def get_living_score(
    unit_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LivingScoreResponse:
    """Compute the deterministic Living Score for a property."""
    return await LivingScoreService(db).get_living_score(unit_id)


@router.post("", response_model=PropertyResponse, status_code=201)
async def create_property(
    payload: PropertyCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, require_roles(UserRole.hoa_admin.value)],
) -> PropertyResponse:
    """Register a new unit/property (HOA admins only)."""
    return await PropertyService(db).create_property(payload)
