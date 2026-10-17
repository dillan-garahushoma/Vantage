"""Estate health brief routes (BATCH AI-4).

Three thin routes over `HealthBriefService`:

* **GET `/analytics/health-brief`** - the brief explaining the estate's latest
  stored score, for any estate member. The stored AI brief if one exists,
  otherwise the deterministic template.
* **POST `/analytics/health-brief`** - ask for the AI brief, for an HOA admin who
  is a member of *that* estate. Idempotent: one brief per score. A failure of any
  kind still answers 200 with the template and a reason code, because the product
  is complete without the AI layer.
* **POST `/analytics/health-brief/{insight_id}/feedback`** - a member's verdict on
  a stored brief, once per member.

The estate always comes from the `estate_id` query parameter and is authorized
against a persisted membership inside the service; it is never taken from a body,
and a client-supplied `estate_id` is never proof of access. Nothing here computes
a score or reads a database row directly.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.schemas.health_brief import (
    HealthBriefFeedbackRequest,
    HealthBriefFeedbackResponse,
    HealthBriefResponse,
)
from app.analytics.services.health_brief_service import HealthBriefService
from app.common.enums import UserRole
from app.db.session import get_db
from app.identity.api.dependencies import CurrentUser, require_roles
from app.identity.models.user import User

router = APIRouter(prefix="/health-brief", tags=["analytics"])

AdminOnly = Annotated[User, require_roles(UserRole.hoa_admin.value)]


@router.get("", response_model=HealthBriefResponse)
async def get_health_brief(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
) -> HealthBriefResponse:
    """The latest brief for this estate. Never calls a provider, never writes."""
    return await HealthBriefService(db).read(estate_id, current_user)


@router.post("", response_model=HealthBriefResponse)
async def generate_health_brief(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
) -> HealthBriefResponse:
    """Generate the brief for the latest score, or return the stored one."""
    return await HealthBriefService(db).generate(estate_id, admin)


@router.post("/{insight_id}/feedback", response_model=HealthBriefFeedbackResponse)
async def submit_health_brief_feedback(
    insight_id: int,
    payload: HealthBriefFeedbackRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
) -> HealthBriefFeedbackResponse:
    """Rate one stored brief. The comment stays in this database."""
    return await HealthBriefService(db).feedback(
        insight_id,
        estate_id,
        current_user,
        helpful=payload.helpful,
        comment=payload.comment,
    )
