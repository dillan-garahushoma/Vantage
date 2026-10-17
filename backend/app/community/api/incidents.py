"""Estate-scoped security incidents (BATCH 6B).

Four routes and no DELETE: an incident is operational history and the Living
Score reads it after the fact. The estate always comes from the `estate_id`
query parameter and is authorized against a persisted membership; it is never
accepted in a request body.

The filter types are `Literal`s built from `incident_vocabulary`, so a filter
outside the controlled vocabulary is a 422 rather than an empty page.
"""
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import ensure_utc
from app.common.enums import UserRole
from app.common.pagination import Page, PaginationParams
from app.community.domain.incident_vocabulary import CATEGORIES, SEVERITIES, STATUSES
from app.community.schemas.security_incident import (
    IncidentCreate,
    IncidentResponse,
    IncidentUpdate,
)
from app.community.services.security_incident_service import SecurityIncidentService
from app.db.session import get_db
from app.identity.api.dependencies import CurrentUser, require_roles
from app.identity.models.user import User

router = APIRouter(prefix="/incidents", tags=["incidents"])

AdminOnly = Annotated[User, require_roles(UserRole.hoa_admin.value)]

CategoryFilter = Literal[*CATEGORIES]
SeverityFilter = Literal[*SEVERITIES]
StatusFilter = Literal[*STATUSES]


@router.get("", response_model=Page[IncidentResponse])
async def list_incidents(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
    pagination: Annotated[PaginationParams, Depends()],
    status: Annotated[StatusFilter | None, Query()] = None,
    severity: Annotated[SeverityFilter | None, Query()] = None,
    category: Annotated[CategoryFilter | None, Query()] = None,
    occurred_from: Annotated[datetime | None, Query()] = None,
    occurred_to: Annotated[datetime | None, Query()] = None,
) -> Page[IncidentResponse]:
    """Every estate member may see that incidents happened."""
    return await SecurityIncidentService(db).list_incidents(
        current_user,
        page=pagination.page,
        size=pagination.size,
        estate_id=estate_id,
        status=status,
        severity=severity,
        category=category,
        occurred_from=ensure_utc(occurred_from),
        occurred_to=ensure_utc(occurred_to),
    )


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
) -> IncidentResponse:
    return await SecurityIncidentService(db).get_incident(
        incident_id, current_user, estate_id=estate_id
    )


@router.post("", response_model=IncidentResponse, status_code=201)
async def create_incident(
    payload: IncidentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
) -> IncidentResponse:
    """Record an incident. The estate is the query's, the author is the admin's."""
    return await SecurityIncidentService(db).create_incident(
        payload, admin, estate_id=estate_id
    )


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: int,
    payload: IncidentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
) -> IncidentResponse:
    """Update severity, status or the resolution notes. `resolved` is terminal."""
    return await SecurityIncidentService(db).update_incident(
        incident_id, payload, admin, estate_id=estate_id
    )
