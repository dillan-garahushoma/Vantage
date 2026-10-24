"""Public provider applications and estate-authorized HOA decisions."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.identity.api.dependencies import require_roles
from app.identity.models.user import User
from app.identity.schemas.provider_invitation import (
    ProviderApplicationCreateRequest,
    ProviderApplicationResponse,
)
from app.identity.services.provider_application_service import ProviderApplicationService

router = APIRouter(prefix="/provider-applications", tags=["identity"])
AdminOnly = Annotated[User, require_roles("hoa_admin")]


@router.post("", response_model=ProviderApplicationResponse, status_code=201)
async def apply_to_estate(
    payload: ProviderApplicationCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderApplicationResponse:
    """Submit an application for HOA review; this does not create an account."""
    return await ProviderApplicationService(db).apply(payload)


@router.get("", response_model=list[ProviderApplicationResponse])
async def list_applications(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
    status: Annotated[Literal["pending", "approved", "rejected"] | None, Query()] = None,
) -> list[ProviderApplicationResponse]:
    return await ProviderApplicationService(db).list_applications(
        admin, estate_id=estate_id, status=status
    )


@router.post("/{application_id}/approve", response_model=ProviderApplicationResponse)
async def approve_application(
    application_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
) -> ProviderApplicationResponse:
    return await ProviderApplicationService(db).approve(
        admin, estate_id=estate_id, application_id=application_id
    )


@router.post("/{application_id}/reject", response_model=ProviderApplicationResponse)
async def reject_application(
    application_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
) -> ProviderApplicationResponse:
    return await ProviderApplicationService(db).reject(
        admin, estate_id=estate_id, application_id=application_id
    )
