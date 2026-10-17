"""The public directory routes: **no authentication of any kind**.

There is deliberately no ``CurrentUser`` dependency in this module and every route
is a read. What is exposed is decided in
:mod:`app.property.services.public_directory_service` and in the allow-list DTOs -
never here - so this file stays a thin, auditable surface:

* ``GET /public/estates`` - published estates only, paginated (``page_size`` ≤ 50);
* ``GET /public/estates/{estate_id}`` - 404 unless the estate is published;
* ``GET /public/photos/{public_id}`` - one stored image by its random handle, with
  ``X-Content-Type-Options: nosniff`` and a one-hour public cache.
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import Page
from app.db.session import get_db
from app.property.schemas.public_directory import (
    PublicEstateDetailResponse,
    PublicEstateListItem,
)
from app.property.services.public_directory_service import PublicDirectoryService

router = APIRouter(prefix="/public", tags=["public"])

#: Photos are immutable once stored (the image is never replaced, only deleted),
#: so a one-hour public cache is safe and cheap. ``nosniff`` stops a browser from
#: re-interpreting the bytes as anything but the declared image type.
PHOTO_CACHE_CONTROL = "public, max-age=3600"
PUBLIC_PHOTO_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": PHOTO_CACHE_CONTROL,
}


@router.get("/estates", response_model=Page[PublicEstateListItem])
async def list_public_estates(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
    q: Annotated[str | None, Query(max_length=80, description="name, suburb or city")] = None,
) -> Page[PublicEstateListItem]:
    """Published estates, with a cover photo and a unit count each."""
    items, total = await PublicDirectoryService(db).list_estates(
        page=page, page_size=page_size, q=q
    )
    return Page[PublicEstateListItem](items=items, total=total, page=page, size=page_size)


@router.get("/estates/{estate_id}", response_model=PublicEstateDetailResponse)
async def get_public_estate(
    estate_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicEstateDetailResponse:
    """One published estate: photos, description, and its score only if opted in."""
    return await PublicDirectoryService(db).get_estate(estate_id)


@router.get("/photos/{public_id}")
async def get_public_photo(
    public_id: Annotated[str, Path(min_length=1, max_length=32)],
    db: Annotated[AsyncSession, Depends(get_db)],
    size: Annotated[Literal["thumb", "full"], Query()] = "full",
) -> Response:
    """One stored image by its public handle, at ``thumb`` or ``full`` size."""
    content, content_type = await PublicDirectoryService(db).read_photo(
        public_id, size=size
    )
    return Response(
        content=content, media_type=content_type, headers=dict(PUBLIC_PHOTO_HEADERS)
    )
