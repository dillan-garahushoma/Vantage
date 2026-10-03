from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ComplaintStatus, UserRole
from app.community.schemas.complaint import (
    ComplaintCreate,
    ComplaintResponse,
    ComplaintStatsResponse,
    ComplaintStatusUpdate,
    PaginatedComplaintsResponse,
)
from app.community.services.complaint_service import ComplaintService
from app.db.session import get_db
from app.identity.api.dependencies import CurrentUser, require_roles
from app.identity.models.user import User

router = APIRouter(prefix="/complaints", tags=["complaints"])

AdminOnly = Annotated[User, require_roles(UserRole.hoa_admin.value)]
ResidentOrAdmin = Annotated[
    User, require_roles(UserRole.resident.value, UserRole.hoa_admin.value)
]


@router.get("", response_model=PaginatedComplaintsResponse)
async def list_complaints(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    unit_id: Annotated[int | None, Query(ge=1)] = None,
    status: Annotated[ComplaintStatus | None, Query()] = None,
    category: Annotated[str | None, Query(max_length=50)] = None,
) -> PaginatedComplaintsResponse:
    """HOA admins see all complaints; other users only see their own."""
    return await ComplaintService(db).list_complaints(
        current_user,
        page=page,
        page_size=page_size,
        unit_id=unit_id,
        status=status.value if status else None,
        category=category,
    )


# NOTE: declared before "/{complaint_id}" so "stats" is not parsed as an id
@router.get("/stats", response_model=ComplaintStatsResponse)
async def complaint_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: AdminOnly,
) -> ComplaintStatsResponse:
    return await ComplaintService(db).get_stats()


@router.get("/{complaint_id}", response_model=ComplaintResponse)
async def get_complaint(
    complaint_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
) -> ComplaintResponse:
    return await ComplaintService(db).get_complaint(complaint_id, current_user)


@router.post("", response_model=ComplaintResponse, status_code=201)
async def create_complaint(
    payload: ComplaintCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: ResidentOrAdmin,
) -> ComplaintResponse:
    """File a complaint. The author is taken from the logged-in user."""
    return await ComplaintService(db).create_complaint(payload, current_user)


@router.patch("/{complaint_id}/status", response_model=ComplaintResponse)
async def update_complaint_status(
    complaint_id: int,
    payload: ComplaintStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
) -> ComplaintResponse:
    return await ComplaintService(db).update_status(complaint_id, payload, admin)
