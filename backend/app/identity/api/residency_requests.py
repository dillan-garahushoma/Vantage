"""Residency-request router: a resident asks, an estate admin decides.

Thin HTTP layer only. Two audiences share the ``/residency-requests`` prefix:

* the **resident** path - ``POST`` to submit and ``GET /mine`` to read their own
  requests. Submitting carries an estate *target* in the body, which is the one
  place an ``estate_id`` from a client is legitimate: the resident is asking to
  join, so it cannot be proof of access, and the service still resolves the estate
  and unit itself.
* the **estate admin** path - the queue, the pending count and the two decision
  endpoints. Every one is estate-scoped by ``?estate_id=`` and the service requires
  an ``hoa_admin`` membership of that estate before anything is read or written.

The decision is the endpoint (``/approve``, ``/reject``); there is no status field
a client can PATCH, so a request cannot be self-approved by editing it.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ResidencyRequestStatus, UserRole
from app.common.pagination import Page
from app.db.session import get_db
from app.identity.api.dependencies import require_roles
from app.identity.models.user import User
from app.identity.schemas.residency_request import (
    PendingResidencyCountResponse,
    ResidencyRequestCreate,
    ResidencyRequestReject,
    ResidencyRequestResponse,
)
from app.identity.services.residency_request_service import ResidencyRequestService

router = APIRouter(prefix="/residency-requests", tags=["identity"])

ResidentOnly = Annotated[User, require_roles(UserRole.resident.value)]
AdminOnly = Annotated[User, require_roles(UserRole.hoa_admin.value)]


@router.post("", response_model=ResidencyRequestResponse, status_code=201)
async def submit_residency_request(
    payload: ResidencyRequestCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    resident: ResidentOnly,
) -> ResidencyRequestResponse:
    """Submit a request to be admitted to one unit of one estate.

    Nothing is granted here: the request is recorded ``pending`` and the estate's
    administrators are notified. A repeat submission while one is pending is a 409,
    and repeated attempts against unknown units are rate-limited.
    """
    return await ResidencyRequestService(db).submit(resident, payload)


@router.get("/mine", response_model=list[ResidencyRequestResponse])
async def my_residency_requests(
    db: Annotated[AsyncSession, Depends(get_db)],
    resident: ResidentOnly,
) -> list[ResidencyRequestResponse]:
    """The requests the caller submitted, newest first, across all estates."""
    return await ResidencyRequestService(db).list_mine(resident)


@router.get("/pending-count", response_model=PendingResidencyCountResponse)
async def pending_residency_count(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
) -> PendingResidencyCountResponse:
    """How many requests this estate has still to decide, for the nav badge."""
    pending = await ResidencyRequestService(db).pending_count(admin, estate_id=estate_id)
    return PendingResidencyCountResponse(pending=pending)


@router.get("", response_model=Page[ResidencyRequestResponse])
async def list_residency_requests(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
    status: Annotated[ResidencyRequestStatus | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=120)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[ResidencyRequestResponse]:
    """One page of this estate's requests, searchable and filterable by status."""
    return await ResidencyRequestService(db).list_for_estate(
        admin,
        estate_id=estate_id,
        status=status.value if status is not None else None,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.post("/{request_id}/approve", response_model=ResidencyRequestResponse)
async def approve_residency_request(
    request_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
) -> ResidencyRequestResponse:
    """Approve a pending request and grant the resident membership of the unit.

    HOA administrators only. A request that another administrator already decided
    is a 409, not an overwrite.
    """
    return await ResidencyRequestService(db).approve(
        admin, estate_id=estate_id, request_id=request_id
    )


@router.post("/{request_id}/reject", response_model=ResidencyRequestResponse)
async def reject_residency_request(
    request_id: int,
    payload: ResidencyRequestReject,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
) -> ResidencyRequestResponse:
    """Decline a pending request, recording an optional reason. HOA admins only."""
    return await ResidencyRequestService(db).reject(
        admin, estate_id=estate_id, request_id=request_id, note=payload.note
    )
