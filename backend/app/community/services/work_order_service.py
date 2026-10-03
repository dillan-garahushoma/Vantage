from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import utcnow
from app.common.enums import UserRole, WorkOrderStatus
from app.community.models.maintenance_work_order import MaintenanceworkOrder
from app.community.repositories.complaint_repository import ComplaintRepository
from app.community.repositories.work_order_repository import WorkOrderRepository
from app.community.schemas.work_order import (
    PaginatedWorkOrdersResponse,
    WorkOrderCreate,
    WorkOrderRating,
    WorkOrderResponse,
    WorkOrderUpdate,
)
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.identity.models.user import User
from app.providers.repositories.service_provider_repository import ServiceProviderRepository


class WorkOrderService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = WorkOrderRepository(db)
        self._complaint_repo = ComplaintRepository(db)
        self._provider_repo = ServiceProviderRepository(db)

    async def _get_or_404(self, work_order_id: int) -> MaintenanceworkOrder:
        work_order = await self._repo.get_by_id(work_order_id)
        if work_order is None:
            raise NotFoundException(f"Work order with id {work_order_id} was not found.")
        return work_order

    async def list_work_orders(
        self,
        *,
        page: int,
        page_size: int,
        complaint_id: int | None = None,
        provider_id: int | None = None,
        status: str | None = None,
    ) -> PaginatedWorkOrdersResponse:
        filters = dict(complaint_id=complaint_id, provider_id=provider_id, status=status)
        work_orders = await self._repo.search(
            offset=(page - 1) * page_size, limit=page_size, **filters
        )
        total = await self._repo.count(**filters)
        return PaginatedWorkOrdersResponse(
            count=total,
            page=page,
            page_size=page_size,
            work_orders=[WorkOrderResponse.model_validate(w) for w in work_orders],
        )

    async def get_work_order(self, work_order_id: int, user: User) -> WorkOrderResponse:
        work_order = await self._get_or_404(work_order_id)
        if user.role != UserRole.hoa_admin.value:
            complaint = await self._complaint_repo.get_by_id(work_order.complaint_id)
            if complaint is None or complaint.user_id != user.user_id:
                raise ForbiddenException("You can only view work orders for your own complaints.")
        return WorkOrderResponse.model_validate(work_order)

    async def create_work_order(self, payload: WorkOrderCreate) -> WorkOrderResponse:
        if await self._complaint_repo.get_by_id(payload.complaint_id) is None:
            raise NotFoundException(f"Complaint with id {payload.complaint_id} was not found.")
        if await self._provider_repo.get_by_id(payload.provider_id) is None:
            raise NotFoundException(
                f"Service provider with id {payload.provider_id} was not found."
            )
        work_order = await self._repo.create(
            complaint_id=payload.complaint_id,
            provider_id=payload.provider_id,
            job_cost=payload.job_cost,
            estimated_completion_date=payload.estimated_completion_date,
        )
        return WorkOrderResponse.model_validate(work_order)

    async def update_work_order(
        self, work_order_id: int, payload: WorkOrderUpdate
    ) -> WorkOrderResponse:
        work_order = await self._get_or_404(work_order_id)
        changes = payload.model_dump(exclude_unset=True)

        new_status = changes.pop("status", None)
        if new_status is not None:
            work_order.status = new_status.value
            if new_status == WorkOrderStatus.completed:
                now = utcnow()
                if work_order.resolved_at is None:
                    work_order.resolved_at = now
                if work_order.actual_completion_date is None:
                    work_order.actual_completion_date = now
            elif new_status in (WorkOrderStatus.assigned, WorkOrderStatus.in_progress):
                # job re-opened after being completed
                work_order.resolved_at = None
                work_order.actual_completion_date = None

        for field, value in changes.items():
            setattr(work_order, field, value)

        work_order = await self._repo.save(work_order)
        return WorkOrderResponse.model_validate(work_order)

    async def rate_work_order(
        self, work_order_id: int, payload: WorkOrderRating, user: User
    ) -> WorkOrderResponse:
        work_order = await self._get_or_404(work_order_id)
        complaint = await self._complaint_repo.get_by_id(work_order.complaint_id)
        if complaint is None or complaint.user_id != user.user_id:
            raise ForbiddenException("Only the resident who raised the complaint can rate the work.")
        if work_order.status != WorkOrderStatus.completed.value:
            raise ConflictException("A work order can only be rated once it is completed.")
        if work_order.resident_rating is not None:
            raise ConflictException("This work order has already been rated.")

        work_order.resident_rating = payload.rating
        work_order = await self._repo.save(work_order)
        return WorkOrderResponse.model_validate(work_order)
