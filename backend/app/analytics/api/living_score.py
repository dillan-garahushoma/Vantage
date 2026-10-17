"""Estate Living Score routes (BATCH 7C).

Three thin routes over `LivingScoreService`:

* **GET `/analytics/living-score`** - the latest stored score, for any estate
  member. 404 when the estate has never been scored, never an empty or partial
  score.
* **POST `/analytics/living-score/recalculate`** - calculate and append a new
  snapshot, for an HOA admin who is a member of *that* estate. 201.
* **GET `/analytics/living-score/history`** - a page of stored snapshots, newest
  first, for any estate member.

The estate always comes from the `estate_id` query parameter and is authorized
against a persisted membership inside the service; it is never taken from a body,
and a client-supplied `estate_id` is never proof of access. Reads project the
stored snapshot and never recalculate it, so a historical value cannot move.

The legacy per-property score route in `app/analytics/api/router.py` is untouched.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.schemas.living_score_snapshot import (
    LivingScoreHistoryResponse,
    LivingScoreSnapshotResponse,
)
from app.analytics.services.estate_living_score_service import LivingScoreService
from app.common.enums import UserRole
from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.identity.api.dependencies import CurrentUser, require_roles
from app.identity.models.user import User

router = APIRouter(prefix="/living-score", tags=["analytics"])

AdminOnly = Annotated[User, require_roles(UserRole.hoa_admin.value)]

NEVER_SCORED_MESSAGE = (
    "No Living Score has been calculated for this estate yet. "
    "An estate administrator can calculate the first one."
)


@router.get("", response_model=LivingScoreSnapshotResponse)
async def get_latest_living_score(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
) -> LivingScoreSnapshotResponse:
    """The estate's most recent stored score. Any estate member may read it."""
    view = await LivingScoreService(db).latest_view(estate_id=estate_id, user=current_user)
    if view is None:
        raise NotFoundException(NEVER_SCORED_MESSAGE)
    return LivingScoreSnapshotResponse.from_stored_snapshot(view.snapshot, is_demo=view.is_demo)


@router.post("/recalculate", response_model=LivingScoreSnapshotResponse, status_code=201)
async def recalculate_living_score(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
) -> LivingScoreSnapshotResponse:
    """Calculate and append a new snapshot. Snapshots are never rewritten."""
    view = await LivingScoreService(db).recalculate_view(estate_id=estate_id, admin=admin)
    return LivingScoreSnapshotResponse.from_stored_snapshot(view.snapshot, is_demo=view.is_demo)


@router.get("/history", response_model=LivingScoreHistoryResponse)
async def get_living_score_history(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
    page: Annotated[int, Query(ge=1, description="1-based page number.")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Snapshots per page.")] = 20,
) -> LivingScoreHistoryResponse:
    """Stored snapshots, newest first. Values are returned exactly as stored."""
    history = await LivingScoreService(db).history(
        estate_id=estate_id, user=current_user, page=page, size=page_size
    )
    return LivingScoreHistoryResponse.from_history(history)
