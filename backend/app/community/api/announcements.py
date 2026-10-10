from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.common.pagination import Page, PaginationParams
from app.community.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementResponse,
    AnnouncementUpdate,
)
from app.community.services.announcement_service import AnnouncementService
from app.db.session import get_db
from app.identity.api.dependencies import CurrentUser, require_roles
from app.identity.models.user import User

router = APIRouter(prefix="/announcements", tags=["announcements"])

AdminOnly = Annotated[User, require_roles(UserRole.hoa_admin.value)]


@router.get("", response_model=Page[AnnouncementResponse])
async def list_announcements(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
    pagination: Annotated[PaginationParams, Depends()],
    include_expired: Annotated[bool, Query(description="HOA admins only")] = False,
) -> Page[AnnouncementResponse]:
    return await AnnouncementService(db).list_announcements(
        current_user,
        page=pagination.page,
        size=pagination.size,
        estate_id=estate_id,
        include_expired=include_expired,
    )


@router.get("/{announcement_id}", response_model=AnnouncementResponse)
async def get_announcement(
    announcement_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
) -> AnnouncementResponse:
    return await AnnouncementService(db).get_announcement(announcement_id, current_user, estate_id=estate_id)


@router.post("", response_model=AnnouncementResponse, status_code=201)
async def create_announcement(
    payload: AnnouncementCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
) -> AnnouncementResponse:
    """Publish an announcement. The author is taken from the logged-in admin."""
    return await AnnouncementService(db).create_announcement(payload, admin, estate_id=estate_id)


@router.patch("/{announcement_id}", response_model=AnnouncementResponse)
async def update_announcement(
    announcement_id: int,
    payload: AnnouncementUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
) -> AnnouncementResponse:
    return await AnnouncementService(db).update_announcement(announcement_id, payload, admin, estate_id=estate_id)


@router.delete("/{announcement_id}", status_code=204)
async def delete_announcement(
    announcement_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
) -> Response:
    await AnnouncementService(db).delete_announcement(announcement_id, admin, estate_id=estate_id)
    return Response(status_code=204)
