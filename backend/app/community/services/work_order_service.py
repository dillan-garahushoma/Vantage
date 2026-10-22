from decimal import Decimal
from types import SimpleNamespace
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import Page
from app.common.datetime_utils import utcnow
from app.common.enums import UserRole, WorkOrderStatus
from app.community.models.maintenance_work_order import MaintenanceworkOrder
from app.community.repositories.complaint_repository import ComplaintRepository
from app.community.repositories.work_order_repository import WorkOrderRepository
from app.community.schemas.work_order import (
    WorkOrderCreate,
    WorkOrderRating,
    WorkOrderResponse,
    WorkOrderUpdate,
)
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.identity.models.user import User
from app.identity.repositories.account_support_repository import AccountSupportRepository
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.providers.repositories.service_provider_repository import ServiceProviderRepository


class WorkOrderService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._notifications = AccountSupportRepository(db)
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
        size: int,
        sort: str = "-created_at",
        complaint_id: int | None = None,
        provider_id: int | None = None,
        status: str | None = None,
        estate_id: int,
        actor: User,
    ) -> Page[WorkOrderResponse]:
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
            offset=(page - 1) * size, limit=size, sort=sort, **filters
        )
        total = await self._repo.count(**filters)
        return Page[WorkOrderResponse](
            items=[WorkOrderResponse.model_validate(w) for w in work_orders],
            total=total,
            page=page,
            size=size,
        )

    async def list_my_work_orders(
        self,
        actor: User,
        *,
        estate_id: int,
        page: int,
        size: int,
        status: str | None = None,
    ) -> Page[WorkOrderResponse]:
        """One page of the work assigned to the signed-in provider in this estate.

        A ``service_provider`` member sees only rows whose ``provider_id`` is their
        own profile. An account with the provider role but no linked profile (or no
        membership) gets an empty page rather than an error: there is simply no
        work to show and nothing about anybody else's is revealed.
        """
        await self._estate_authorization.require_role(
            actor=actor,
            estate_id=estate_id,
            allowed_roles=(UserRole.service_provider.value,),
        )
        provider = await self._provider_repo.get_by_user_id(actor.user_id)
        if provider is None:
            return Page[WorkOrderResponse](items=[], total=0, page=page, size=size)

        filters = dict(
            complaint_id=None,
            estate_id=estate_id,
            provider_id=provider.provider_id,
            status=status,
        )
        work_orders = await self._repo.search(
            offset=(page - 1) * size, limit=size, sort="-created_at", **filters
        )
        total = await self._repo.count(**filters)
        return Page[WorkOrderResponse](
            items=[WorkOrderResponse.model_validate(w) for w in work_orders],
            total=total,
            page=page,
            size=size,
        )

    async def get_for_complaint(
        self, complaint_id: int, actor: User, *, estate_id: int
    ) -> WorkOrderResponse:
        """The work order raised for one complaint: its author, or an estate admin.

        Any other member of the estate is a 403 (they are a member but the
        complaint is not theirs) and a complaint from another estate is a 404.
        """
        access = await self._estate_authorization.resolve_access(actor, estate_id=estate_id)
        complaint = await self._complaint_repo.get_by_id_in_estate(
            complaint_id=complaint_id, estate_id=estate_id
        )
        if complaint is None:
            raise NotFoundException(f"Complaint with id {complaint_id} was not found.")
        if not access.is_estate_admin and complaint.user_id != actor.user_id:
            raise ForbiddenException(
                "You can only view the work order for your own complaint."
            )
        work_order = await self._repo.get_latest_for_complaint(
            complaint_id=complaint_id, estate_id=estate_id
        )
        if work_order is None:
            raise NotFoundException(
                f"No work order has been created for complaint {complaint_id} yet."
            )
        return WorkOrderResponse.model_validate(work_order)

    async def get_work_order(
        self, work_order_id: int, user: User, *, estate_id: int
    ) -> WorkOrderResponse:
        access = await self._estate_authorization.resolve_access(
            user, estate_id=estate_id
        )
        work_order = await self._get_or_404_in_estate(
            work_order_id=work_order_id, estate_id=estate_id
        )
        if access.is_estate_provider:
            provider = await self._provider_repo.get_by_user_id(user.user_id)
            if provider is None or provider.provider_id != work_order.provider_id:
                raise ForbiddenException("You can only view work assigned to your provider profile.")
        elif not access.is_estate_admin:
            complaint = await self._complaint_repo.get_by_id_in_estate(
                complaint_id=work_order.complaint_id, estate_id=estate_id
            )
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
        assert complaint.estate_id == estate_id

        # C1: require complaint status to be 'reviewed'
        if complaint.status != "reviewed":
            raise ConflictException(
                f"Work order can only be created for a reviewed complaint. Current status: '{complaint.status}'."
            )

        # C1: reject second active work order for the same complaint
        if hasattr(self._repo, "get_active_for_complaint"):
            active_wo = await self._repo.get_active_for_complaint(
                complaint_id=payload.complaint_id, estate_id=estate_id)
            if active_wo is not None:
                raise ConflictException("An active work order already exists for this complaint.")

        provider = await self._provider_repo.get_by_id_in_estate(
            provider_id=payload.provider_id, estate_id=estate_id)
        if provider is None:
            raise NotFoundException(
                f"Service provider with id {payload.provider_id} was not found."
            )
        if provider.user_id is None:
            raise ConflictException("The selected provider must have a linked service-provider account.")

        # C1: verify provider's linked user has service_provider membership in this estate
        provider_user_obj = SimpleNamespace(user_id=provider.user_id, role=UserRole.service_provider.value)
        try:
            prov_access = await self._estate_authorization.resolve_access(provider_user_obj, estate_id)
            if not prov_access.is_estate_provider:
                raise ConflictException("Provider user does not have a service_provider membership in this estate.")
        except ForbiddenException:
            raise ConflictException("Provider user does not have a membership in this estate.")

        # Atomicity: create work order, move complaint to assigned, record assigned event in one commit
        try:
            commit_repo = not hasattr(self, "_db") or self._db is None
            work_order = await self._repo.create(
                complaint_id=payload.complaint_id,
                estate_id=estate_id,
                provider_id=payload.provider_id,
                job_cost=payload.job_cost,
                estimated_completion_date=payload.estimated_completion_date,
                commit=commit_repo,
            )
            old_status = complaint.status
            complaint.status = "assigned"
            complaint.assigned_at = utcnow()
            complaint.assigned_to = provider.full_name
            await self._complaint_repo.record_transition(
                complaint=complaint,
                actor_user_id=admin.user_id,
                from_status=old_status,
                to_status="assigned",
                note=f"Assigned to {provider.full_name}",
                commit=commit_repo,
            )
            if not commit_repo:
                await self._notifications.notify(estate_id=estate_id,
                    user_ids={complaint.user_id, provider.user_id}, kind='work_order_assigned',
                    resource_id=work_order.work_order_id)
                await self._db.commit()
                await self._db.refresh(work_order)
            return WorkOrderResponse.model_validate(work_order)
        except Exception:
            if hasattr(self, "_db") and self._db is not None:
                await self._db.rollback()
            raise

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
        if work_order.status in ('completed', 'cancelled'):
            raise ConflictException('A completed work order cannot be re-opened or modified; cancelled work is also terminal.')
        new_status = changes.pop("status", None)

        if new_status is not None:
            # C2 state machine: allowed: assigned -> in_progress -> completed
            # Providers may NOT set 'assigned' or 'cancelled' in this pass
            if new_status in (WorkOrderStatus.assigned, WorkOrderStatus.cancelled):
                raise ConflictException(f"Providers cannot transition work order to '{new_status.value}'.")

            # Completed is terminal; cannot re-open
            if work_order.status == WorkOrderStatus.completed.value:
                raise ConflictException("A completed work order cannot be re-opened or modified.")

            # completed requires current status in_progress
            if new_status == WorkOrderStatus.completed and work_order.status != WorkOrderStatus.in_progress.value:
                raise ConflictException("Work order must be in_progress before it can be marked completed.")

            if new_status == WorkOrderStatus.in_progress and work_order.status != WorkOrderStatus.assigned.value:
                raise ConflictException(f"Cannot transition work order from '{work_order.status}' to 'in_progress'.")

            complaint = await self._complaint_repo.get_by_id_in_estate(
                complaint_id=work_order.complaint_id, estate_id=estate_id
            )
            if complaint is None:
                raise NotFoundException("The work order's complaint was not found.")

            work_order.status = new_status.value
            now = utcnow()
            try:
                commit_repo = not hasattr(self, "_db") or self._db is None
                if new_status == WorkOrderStatus.in_progress:
                    if complaint.status == "assigned":
                        complaint.status = "in_progress"
                        complaint.started_at = now
                        await self._complaint_repo.record_transition(
                            complaint=complaint,
                            actor_user_id=provider_user.user_id,
                            from_status="assigned",
                            to_status="in_progress",
                            note=None,
                            commit=commit_repo,
                        )
                elif new_status == WorkOrderStatus.completed:
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
                            commit=commit_repo,
                        )
                for field, value in changes.items():
                    setattr(work_order, field, value)
                await self._repo.save(work_order, commit=commit_repo)
                if not commit_repo:
                    await self._notifications.notify(estate_id=estate_id, user_ids={complaint.user_id},
                        kind='work_order_' + work_order.status, resource_id=work_order.work_order_id)
                    await self._notifications.notify_admins(estate_id=estate_id,
                        kind='work_order_' + work_order.status, resource_id=work_order.work_order_id)
                    await self._db.commit()
                    await self._db.refresh(work_order)
                return WorkOrderResponse.model_validate(work_order)
            except Exception:
                if hasattr(self, "_db") and self._db is not None:
                    await self._db.rollback()
                raise

        for field, value in changes.items():
            setattr(work_order, field, value)
        work_order = await self._repo.save(work_order, commit=True)
        return WorkOrderResponse.model_validate(work_order)

    async def rate_work_order(
        self, work_order_id: int, payload: WorkOrderRating, user: User, *, estate_id: int
    ) -> WorkOrderResponse:
        await self._estate_authorization.require_role(
            actor=user, estate_id=estate_id, allowed_roles=(UserRole.resident.value,)
        )
        try:
            # Row lock inside one transaction
            if hasattr(self._repo, "get_by_id_in_estate_for_update"):
                work_order = await self._repo.get_by_id_in_estate_for_update(
                    work_order_id=work_order_id, estate_id=estate_id
                )
            else:
                work_order = await self._repo.get_by_id_in_estate(
                    work_order_id=work_order_id, estate_id=estate_id
                )
            if work_order is None:
                raise NotFoundException(f"Work order with id {work_order_id} was not found.")

            # B4: Defense in depth - scoped getter
            complaint = await self._complaint_repo.get_by_id_in_estate(
                complaint_id=work_order.complaint_id, estate_id=estate_id
            )
            if complaint is None or complaint.user_id != user.user_id:
                raise ForbiddenException("Only the resident who raised the complaint can rate the work.")
            if work_order.status != WorkOrderStatus.completed.value:
                raise ConflictException("A work order can only be rated once it is completed.")
            if work_order.resident_rating is not None:
                raise ConflictException("This work order has already been rated.")
            if complaint.status != 'resolved':
                raise ConflictException('A prior repair cannot close a reopened complaint.')
            latest = await self._repo.get_latest_for_complaint(
                complaint_id=work_order.complaint_id, estate_id=estate_id)
            if latest is None or latest.work_order_id != work_order_id:
                raise ConflictException('Only the latest repair can rate the current resolution.')

            commit_repo = not hasattr(self, "_db") or self._db is None
            work_order.resident_rating = payload.rating
            await self._repo.save(work_order, commit=commit_repo)

            # Move complaint resolved -> rated
            old_complaint_status = complaint.status
            complaint.status = "rated"
            await self._complaint_repo.record_transition(
                complaint=complaint,
                actor_user_id=user.user_id,
                from_status=old_complaint_status,
                to_status="rated",
                note=f"Resident rating: {payload.rating}",
                commit=commit_repo,
            )

            # C3: Recompute provider's avg_rating and total_reviews
            if hasattr(self._repo, "get_provider_rating_aggregate"):
                avg_rating, total_reviews = await self._repo.get_provider_rating_aggregate(
                    provider_id=work_order.provider_id
                )
                provider = await self._provider_repo.get_by_id(work_order.provider_id)
                if provider is not None:
                    if avg_rating is not None:
                        provider.avg_rating = avg_rating.quantize(Decimal("0.01"))
                    provider.total_reviews = total_reviews
                    if hasattr(self._provider_repo, "save"):
                        await self._provider_repo.save(provider)

            if not commit_repo:
                await self._db.commit()
                await self._db.refresh(work_order)
            return WorkOrderResponse.model_validate(work_order)
        except Exception:
            if hasattr(self, "_db") and self._db is not None:
                await self._db.rollback()
            raise
