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
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.providers.repositories.service_provider_repository import ServiceProviderRepository


class WorkOrderService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = WorkOrderRepository(db)
        self._complaint_repo = ComplaintRepository(db)
        self._provider_repo = ServiceProviderRepository(db)
        self._estate_authorization = EstateAuthorizationService(db)

    async def _get_or_404_in_estate(
        self, *, work_order_id: int, estate_id: int
    ) -> MaintenanceworkOrder:
        work_order = await self._repo.get_by_id_in_estate(
            work_order_id=work_order_id, estate_id=estate_id
        )
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
        estate_id: int,
        actor: User,
    ) -> PaginatedWorkOrdersResponse:
        await self._estate_authorization.require_role(
            actor=actor, estate_id=estate_id, allowed_roles=(UserRole.hoa_admin.value,)
        )
        filters = dict(
            complaint_id=complaint_id,
            provider_id=provider_id,
            estate_id=estate_id,
            status=status,
        )
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

    async def get_work_order(
        self, work_order_id: int, user: User, *, estate_id: int
    ) -> WorkOrderResponse:
        await self._estate_authorization.require_membership(
            user_id=user.user_id, estate_id=estate_id
        )
        work_order = await self._get_or_404_in_estate(
            work_order_id=work_order_id, estate_id=estate_id
        )
        if user.role == UserRole.service_provider.value:
            provider = await self._provider_repo.get_by_user_id(user.user_id)
            if provider is None or provider.provider_id != work_order.provider_id:
                raise ForbiddenException("You can only view work assigned to your provider profile.")
        elif user.role != UserRole.hoa_admin.value:
            complaint = await self._complaint_repo.get_by_id(work_order.complaint_id)
            if complaint is None or complaint.user_id != user.user_id:
                raise ForbiddenException("You can only view work orders for your own complaints.")
        return WorkOrderResponse.model_validate(work_order)

    async def create_work_order(
        self, payload: WorkOrderCreate, admin: User, *, estate_id: int
    ) -> WorkOrderResponse:
        await self._estate_authorization.require_role(
            actor=admin, estate_id=estate_id, allowed_roles=(UserRole.hoa_admin.value,)
        )
        complaint = await self._complaint_repo.get_by_id_in_estate(
            complaint_id=payload.complaint_id, estate_id=estate_id
        )
        if complaint is None:
            raise NotFoundException(f"Complaint with id {payload.complaint_id} was not found.")
        provider = await self._provider_repo.get_by_id(payload.provider_id)
        if provider is None:
            raise NotFoundException(
                f"Service provider with id {payload.provider_id} was not found."
            )
        if provider.user_id is None:
            raise ConflictException("The selected provider must have a linked service-provider account.")
        work_order = await self._repo.create(
            complaint_id=payload.complaint_id,
            estate_id=estate_id,
            provider_id=payload.provider_id,
            job_cost=payload.job_cost,
            estimated_completion_date=payload.estimated_completion_date,
        )
        return WorkOrderResponse.model_validate(work_order)

    async def update_work_order(
        self, work_order_id: int, payload: WorkOrderUpdate, provider_user: User, *, estate_id: int
    ) -> WorkOrderResponse:
        await self._estate_authorization.require_role(
            actor=provider_user, estate_id=estate_id, allowed_roles=(UserRole.service_provider.value,)
        )
        work_order = await self._get_or_404_in_estate(
            work_order_id=work_order_id, estate_id=estate_id
        )
        provider = await self._provider_repo.get_by_user_id(provider_user.user_id)
        if provider is None or provider.provider_id != work_order.provider_id:
            raise ForbiddenException("You can only update work assigned to your provider profile.")
        changes = payload.model_dump(exclude_unset=True)

        new_status = changes.pop("status", None)
        if new_status is not None:
            complaint = await self._complaint_repo.get_by_id_in_estate(
                complaint_id=work_order.complaint_id, estate_id=estate_id
            )
            if complaint is None:
                raise NotFoundException("The work order's complaint was not found.")
            work_order.status = new_status.value
            if new_status == WorkOrderStatus.completed:
                now = utcnow()
                if work_order.resolved_at is None:
                    work_order.resolved_at = now
                if work_order.actual_completion_date is None:
                    work_order.actual_completion_date = now
                if complaint.status == "in_progress":
                    complaint.status = "resolved"
                    complaint.resolved_at = now
                    await self._complaint_repo.record_transition(
                        complaint=complaint,
                        actor_user_id=provider_user.user_id,
                        from_status="in_progress",
                        to_status="resolved",
                        note=changes.get("completion_notes"),
                    )
            elif new_status in (WorkOrderStatus.assigned, WorkOrderStatus.in_progress):
                # job re-opened after being completed
                work_order.resolved_at = None
                work_order.actual_completion_date = None
                if new_status == WorkOrderStatus.in_progress and complaint.status == "assigned":
                    complaint.status = "in_progress"
                    complaint.started_at = utcnow()
                    await self._complaint_repo.record_transition(
                        complaint=complaint,
                        actor_user_id=provider_user.user_id,
                        from_status="assigned",
                        to_status="in_progress",
                        note=None,
                    )

        for field, value in changes.items():
            setattr(work_order, field, value)

        work_order = await self._repo.save(work_order)
        return WorkOrderResponse.model_validate(work_order)

    async def rate_work_order(
        self, work_order_id: int, payload: WorkOrderRating, user: User, *, estate_id: int
    ) -> WorkOrderResponse:
        await self._estate_authorization.require_role(
            actor=user, estate_id=estate_id, allowed_roles=(UserRole.resident.value,)
        )
        work_order = await self._get_or_404_in_estate(
            work_order_id=work_order_id, estate_id=estate_id
        )
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
