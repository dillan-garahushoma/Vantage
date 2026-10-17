"""Membership router: a resident's self-service join and an admin's member list.

Two different audiences share this prefix:

* ``POST /memberships/join`` is the resident path. It takes no ``estate_id`` at
  all - the estate comes from the join code, which is the point of the code - and
  it is gated to the ``resident`` role at the route and re-checked in the service.
* ``GET /memberships`` and ``DELETE /memberships/{id}`` are the estate admin path.
  Both are estate-scoped by ``?estate_id=`` and the service requires an
  ``hoa_admin`` membership of that estate before anything is read or written.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.common.pagination import Page
from app.db.session import get_db
from app.identity.api.dependencies import require_roles
from app.identity.models.user import User
from app.identity.schemas.membership import (
    MembershipJoinRequest,
    MembershipJoinResponse,
    MembershipProviderAddRequest,
    MembershipResponse,
)
from app.identity.services.membership_service import MembershipService

router = APIRouter(prefix="/memberships", tags=["identity"])

ResidentOnly = Annotated[User, require_roles(UserRole.resident.value)]
AdminOnly = Annotated[User, require_roles(UserRole.hoa_admin.value)]


@router.get("", response_model=Page[MembershipResponse])
async def list_members(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
    role: Annotated[str | None, Query(max_length=32)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[MembershipResponse]:
    """List this estate's members, newest first."""
    return await MembershipService(db).list_members(
        admin, estate_id=estate_id, role=role, page=page, page_size=page_size
    )


@router.post("/join", response_model=MembershipJoinResponse, status_code=201)
async def join_estate(
    payload: MembershipJoinRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    resident: ResidentOnly,
) -> MembershipJoinResponse:
    """Join the estate your code belongs to, against your unit number.

    No approval step: the code and the unit number are the whole proof. A
    mistyped or unusable code is a uniform 404, and five of them in fifteen
    minutes is a 429.
    """
    return await MembershipService(db).join_with_code(resident, payload)


@router.post("/providers", response_model=MembershipResponse, status_code=201)
async def add_provider_member(
    payload: MembershipProviderAddRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
) -> MembershipResponse:
    """Add an already-registered service provider to this estate, by email.

    The service owns the one commit (membership + ``joined`` event) and answers a
    single uniform 404 for every email that is not a registered provider, 409
    when they are already a member, and 429 after five failed lookups.
    """
    return await MembershipService(db).add_provider_by_email(
        admin, estate_id=estate_id, email=str(payload.email)
    )


@router.delete("/{membership_id}", status_code=204)
async def remove_member(
    membership_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
) -> None:
    """Remove a resident or provider membership of this estate."""
    await MembershipService(db).remove_member(
        admin, membership_id=membership_id, estate_id=estate_id
    )
