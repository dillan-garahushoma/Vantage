from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import Page
from app.analytics.schemas.living_score import LegacyPropertyScoreResponse
from app.analytics.services.living_score_service import LegacyPropertyScoreService
from app.db.session import get_db
from app.identity.api.dependencies import CurrentUser
from app.property.schemas.property import (
    BulkUnitsRequest,
    PropertyCreate,
    PropertyResponse,
    PropertyUpdate,
)
from app.property.services.property_service import PropertyService
from app.property.services.property_photo_service import PropertyPhotoService
from app.property.domain.photo_pipeline import MAX_UPLOAD_BYTES

router = APIRouter(prefix="/properties", tags=["property"])


@router.patch('/{unit_id}', response_model=PropertyResponse)
async def update_property(
    unit_id: int,
    payload: PropertyUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
) -> PropertyResponse:
    return await PropertyService(db).update_property(unit_id, payload, current_user, estate_id=estate_id)


@router.get("", response_model=Page[PropertyResponse])
async def search_properties(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    bedrooms: Annotated[int | None, Query(ge=0, description="Exact number of bedrooms")] = None,
    bathrooms: Annotated[int | None, Query(ge=0, description="Exact number of bathrooms")] = None,
    min_size_m2: Annotated[Decimal | None, Query(ge=0, description="Minimum size in m²")] = None,
    max_size_m2: Annotated[Decimal | None, Query(ge=0, description="Maximum size in m²")] = None,
    estate_id: Annotated[int, Query(gt=0)] = ...,
) -> Page[PropertyResponse]:
    """List properties, optionally filtered by bedrooms, bathrooms, and size range."""
    return await PropertyService(db).search_properties(
        page=page,
        size=size,
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


@router.get(
    "/{unit_id}/living-score",
    response_model=LegacyPropertyScoreResponse,
    deprecated=True,
)
async def get_living_score(
    unit_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    estate_id: Annotated[int, Query(gt=0)],
    current_user: CurrentUser,
) -> LegacyPropertyScoreResponse:
    """Read the legacy property score only inside an authorized estate scope."""
    await PropertyService(db).get_property(
        unit_id=unit_id, estate_id=estate_id, actor=current_user
    )
    return await LegacyPropertyScoreService(db).get_living_score(unit_id)


@router.post("", response_model=PropertyResponse, status_code=201)
async def create_property(
    payload: PropertyCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
) -> PropertyResponse:
    """Register a new unit/property (HOA admins only)."""
    return await PropertyService(db).create_property(payload, current_user)


@router.post("/bulk", response_model=list[PropertyResponse], status_code=201)
async def create_units_bulk(
    payload: BulkUnitsRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
) -> list[PropertyResponse]:
    """Create up to 500 units in one estate, all or nothing.

    The estate is required as a query parameter and the caller must be an
    ``hoa_admin`` *member* of it. ``complex_name`` and ``suburb`` come from the
    estate, never from the body.
    """
    return await PropertyService(db).create_units_bulk(
        payload, estate_id=estate_id, actor=current_user
    )



@router.get("/{unit_id}/photos")
async def list_unit_photos(
    unit_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
) -> list[dict]:
    """List photos for a unit within the caller's authorised estate."""
    return await PropertyPhotoService(db).list_photos(
        property_id=unit_id, estate_id=estate_id, actor=current_user
    )


@router.post("/{unit_id}/photos", status_code=status.HTTP_201_CREATED)
async def upload_unit_photo(
    unit_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
    file: Annotated[UploadFile, File(description="JPEG, PNG or WebP, at most 5 MB")],
    caption: Annotated[str | None, Form(max_length=140)] = None,
) -> dict:
    """Upload a unit showcase photo; only an HOA administrator of that estate may write."""
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    return await PropertyPhotoService(db).upload_photo(
        property_id=unit_id,
        estate_id=estate_id,
        actor=current_user,
        filename=file.filename,
        content_type=file.content_type,
        data=data,
        caption=caption,
    )


@router.get("/{unit_id}/photos/{photo_id}/image")
async def read_unit_photo(
    unit_id: int,
    photo_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
    size: Annotated[Literal["thumb", "full"], Query()] = "thumb",
) -> Response:
    """Read a unit photo inside the authenticated estate boundary, including unpublished listings."""
    content, content_type = await PropertyPhotoService(db).read_photo(
        property_id=unit_id, photo_id=photo_id, estate_id=estate_id, actor=current_user, size=size
    )
    return Response(
        content=content,
        media_type=content_type,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
    )


@router.delete("/{unit_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit_photo(
    unit_id: int,
    photo_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
) -> None:
    """Delete a unit showcase photo; only an HOA administrator of that estate may write."""
    await PropertyPhotoService(db).delete_photo(
        property_id=unit_id, photo_id=photo_id, estate_id=estate_id, actor=current_user
    )
