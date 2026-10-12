"""Estate profile and photo routes.

Thin HTTP layer only: DTOs, dependency wiring, and the multipart plumbing. All
authorization and every rule (how many photos, what is a valid image, what lands
on disk) lives in the services.

Estate-scoped throughout by ``?estate_id=``. Reads of the profile and the photo
list are open to any member of the estate; every write requires an ``hoa_admin``
membership of it, re-checked inside the service - a client-supplied ``estate_id``
is never proof of access.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.identity.api.dependencies import CurrentUser
from app.property.domain.photo_pipeline import MAX_UPLOAD_BYTES
from app.property.schemas.estate_profile import (
    EstatePhotoResponse,
    EstatePhotoUpdate,
    EstateProfileResponse,
    EstateProfileUpdate,
)
from app.property.services.estate_photo_service import EstatePhotoService
from app.property.services.estate_profile_service import EstateProfileService

router = APIRouter(prefix="/estates", tags=["estates"])


@router.get("/profile", response_model=EstateProfileResponse)
async def get_estate_profile(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
) -> EstateProfileResponse:
    """The estate profile. Any member of the estate may read it."""
    return await EstateProfileService(db).get_profile(current_user, estate_id=estate_id)


@router.patch("/profile", response_model=EstateProfileResponse)
async def update_estate_profile(
    payload: EstateProfileUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
) -> EstateProfileResponse:
    """Change the description and/or the publish switches. HOA admins only.

    The name is not part of this contract, and an unknown field is a 422 rather
    than a silent no-op.
    """
    return await EstateProfileService(db).update_profile(
        current_user, estate_id=estate_id, payload=payload
    )


@router.get("/photos", response_model=list[EstatePhotoResponse])
async def list_estate_photos(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
) -> list[EstatePhotoResponse]:
    """The estate's photos in display order. Any member of the estate may read."""
    return await EstatePhotoService(db).list_photos(current_user, estate_id=estate_id)


@router.post("/photos", response_model=EstatePhotoResponse, status_code=201)
async def upload_estate_photo(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
    file: Annotated[UploadFile, File(description="JPEG, PNG or WebP, at most 5 MB")],
    caption: Annotated[str | None, Form(max_length=140)] = None,
) -> EstatePhotoResponse:
    """Upload one photo, re-encoded and stored server-side under a random id.

    The bytes are read with a hard ceiling (never the whole file into memory
    first), then decoded, capped and re-encoded by the service. The uploaded
    filename is ignored.
    """
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    return await EstatePhotoService(db).upload_photo(
        current_user,
        estate_id=estate_id,
        filename=file.filename,
        content_type=file.content_type,
        data=data,
        caption=caption,
    )


@router.patch("/photos/{photo_id}", response_model=EstatePhotoResponse)
async def update_estate_photo(
    photo_id: int,
    payload: EstatePhotoUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
) -> EstatePhotoResponse:
    """Re-caption or reorder one photo. HOA admins only; the image is immutable."""
    return await EstatePhotoService(db).update_photo(
        current_user, estate_id=estate_id, photo_id=photo_id, payload=payload
    )


@router.delete("/photos/{photo_id}", status_code=204)
async def delete_estate_photo(
    photo_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
) -> None:
    """Delete one photo's row and its files. HOA admins only."""
    await EstatePhotoService(db).delete_photo(
        current_user, estate_id=estate_id, photo_id=photo_id
    )
