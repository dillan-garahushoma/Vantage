from typing import Annotated
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import Page
from app.common.enums import ComplaintStatus, UserRole
from app.community.schemas.complaint import (
    ComplaintCreate,
    ComplaintEventResponse,
    ComplaintResponse,
    ComplaintStatsResponse,
    ComplaintStatusUpdate,
    ComplaintReopen,
)
from app.community.schemas.complaint_ai import (
    TriageDecisionRequest,
    TriageSuggestionResponse,
)
from app.community.schemas.work_order import WorkOrderResponse
from app.community.services.complaint_service import ComplaintService
from app.community.services.complaint_triage_service import ComplaintTriageService
from app.community.services.work_order_service import WorkOrderService
from app.db.session import get_db
from app.identity.api.dependencies import CurrentUser, require_roles
from app.identity.models.user import User

router = APIRouter(prefix="/complaints", tags=["complaints"])

AdminOnly = Annotated[User, require_roles(UserRole.hoa_admin.value)]
ResidentOrAdmin = Annotated[
    User, require_roles(UserRole.resident.value, UserRole.hoa_admin.value)
]


@router.post('/{complaint_id}/reopen', response_model=ComplaintResponse)
async def reopen_complaint(
    complaint_id: int,
    payload: ComplaintReopen,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor: ResidentOrAdmin,
    estate_id: Annotated[int, Query(gt=0)],
) -> ComplaintResponse:
    return await ComplaintService(db).reopen(complaint_id, payload.note, actor, estate_id=estate_id)


@router.get("", response_model=Page[ComplaintResponse])
async def list_complaints(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Literal[
        "created_at", "-created_at", "priority", "-priority", "status", "-status"
    ] = Query(default="-created_at"),
    unit_id: Annotated[int | None, Query(ge=1)] = None,
    status: Annotated[ComplaintStatus | None, Query()] = None,
    category: Annotated[str | None, Query(max_length=50)] = None,
) -> Page[ComplaintResponse]:
    """HOA admins see all complaints; other users only see their own."""
    return await ComplaintService(db).list_complaints(
        current_user,
        page=page,
        size=size,
        sort=sort,
        unit_id=unit_id,
        status=status.value if status else None,
        category=category,
        estate_id=estate_id,
    )


# NOTE: declared before "/{complaint_id}" so "stats" is not parsed as an id
@router.get("/stats", response_model=ComplaintStatsResponse)
async def complaint_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
) -> ComplaintStatsResponse:
    return await ComplaintService(db).get_stats(admin, estate_id=estate_id)


@router.get("/{complaint_id}", response_model=ComplaintResponse)
async def get_complaint(
    complaint_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
) -> ComplaintResponse:
    return await ComplaintService(db).get_complaint(
        complaint_id, current_user, estate_id=estate_id
    )


@router.get("/{complaint_id}/work-order", response_model=WorkOrderResponse)
async def get_complaint_work_order(
    complaint_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
) -> WorkOrderResponse:
    """The work order raised for this complaint.

    Read by the complaint's author (so they can see progress without being able
    to list the estate's work) or by an HOA admin of the estate. The DTO is the
    existing work-order response, unchanged.
    """
    return await WorkOrderService(db).get_for_complaint(
        complaint_id, current_user, estate_id=estate_id
    )


@router.get("/{complaint_id}/events", response_model=list[ComplaintEventResponse])
async def list_complaint_events(
    complaint_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
) -> list[ComplaintEventResponse]:
    return await ComplaintService(db).list_events(
        complaint_id, current_user, estate_id=estate_id
    )


@router.post("", response_model=ComplaintResponse, status_code=201)
async def create_complaint(
    payload: ComplaintCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: ResidentOrAdmin,
    estate_id: Annotated[int, Query(gt=0)],
) -> ComplaintResponse:
    """File a complaint. The author is taken from the logged-in user."""
    return await ComplaintService(db).create_complaint(
        payload, current_user, estate_id=estate_id
    )


@router.patch("/{complaint_id}/status", response_model=ComplaintResponse)
async def update_complaint_status(
    complaint_id: int,
    payload: ComplaintStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
) -> ComplaintResponse:
    return await ComplaintService(db).update_status(
        complaint_id, payload, admin, estate_id=estate_id
    )


# ---------------------------------------------------------------------------- #
# Advisory AI triage suggestions (BATCH AI-3).
#
# Advisory only: these endpoints read and label a suggestion and never modify
# the complaint. They are HOA-admin-only, and the service re-checks the estate
# membership before anything is read, written or sent to a provider. When the AI
# layer is off or fails, they answer 503 and the complaint workflow is unchanged.
# ---------------------------------------------------------------------------- #


@router.post("/{complaint_id}/ai-suggestion", response_model=TriageSuggestionResponse)
async def request_ai_suggestion(
    complaint_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
) -> TriageSuggestionResponse:
    """Ask for the triage suggestion for one complaint.

    Idempotent: the first call asks the AI layer and stores exactly one
    suggestion; later calls return the stored row without another provider call.
    """
    return await ComplaintTriageService(db).generate(complaint_id, estate_id, admin)


@router.get("/{complaint_id}/ai-suggestion", response_model=TriageSuggestionResponse)
async def get_ai_suggestion(
    complaint_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
) -> TriageSuggestionResponse:
    """Return the stored suggestion, or 404 when none has been requested."""
    return await ComplaintTriageService(db).get(complaint_id, estate_id, admin)


@router.post(
    "/{complaint_id}/ai-suggestion/decision",
    response_model=TriageSuggestionResponse,
)
async def decide_ai_suggestion(
    complaint_id: int,
    payload: TriageDecisionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminOnly,
    estate_id: Annotated[int, Query(gt=0)],
) -> TriageSuggestionResponse:
    """Accept, override or dismiss the suggestion. Write-once."""
    return await ComplaintTriageService(db).decide(complaint_id, estate_id, payload, admin)
