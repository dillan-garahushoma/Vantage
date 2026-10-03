from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole, WorkOrderStatus
from app.community.schemas.work_order import (
    PaginatedWorkOrdersResponse,
    WorkOrderCreate,
    WorkOrderRating,
    WorkOrderResponse,
    WorkOrderUpdate,
)
from app.community.services.work_order_service import WorkOrderService
from app.db.session import get_db
from app.identity.api.dependencies import CurrentUser, require_roles
from app.identity.models.user import User

router = APIRouter(prefix="/work-orders", tags=["work orders"])

AdminOnly = Annotated[User, require_roles(UserRole.hoa_admin.value)]
ResidentOnly = Annotated[User, require_roles(UserRole.resident.value)]


@router.get("", response_model=PaginatedWorkOrdersResponse)
async def list_work_orders(
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: AdminOnly,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    complaint_id: Annotated[int | None, Query(ge=1)] = None,
    provider_id: Annotated[int | None, Query(ge=1)] = None,
    status: Annotated[WorkOrderStatus | None, Query()] = None,
) -> PaginatedWorkOrdersResponse:
    return await WorkOrderService(db).list_work_orders(
        page=page,
        page_size=page_size,
        complaint_id=complaint_id,
        provider_id=provider_id,
        status=status.value if status else None,
    )


@router.get("/{work_order_id}", response_model=WorkOrderResponse)
async def get_work_order(
    work_order_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
) -> WorkOrderResponse:
    """HOA admins, or the resident who raised the linked complaint."""
    return await WorkOrderService(db).get_work_order(work_order_id, current_user)


@router.post("", response_model=WorkOrderResponse, status_code=201)
async def create_work_order(
    payload: WorkOrderCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: AdminOnly,
) -> WorkOrderResponse:
    """Assign a service provider to a complaint."""
    return await WorkOrderService(db).create_work_order(payload)


@router.patch("/{work_order_id}", response_model=WorkOrderResponse)
async def update_work_order(
    work_order_id: int,
    payload: WorkOrderUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: AdminOnly,
) -> WorkOrderResponse:
    """Update status, cost, completion notes or estimated date."""
    return await WorkOrderService(db).update_work_order(work_order_id, payload)


@router.post("/{work_order_id}/rating", response_model=WorkOrderResponse)
async def rate_work_order(
    work_order_id: int,
    payload: WorkOrderRating,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: ResidentOnly,
) -> WorkOrderResponse:
    """Resident rates (1-5) a completed job. Feeds the Living Score maintenance factor."""
    return await WorkOrderService(db).rate_work_order(work_order_id, payload, current_user)
