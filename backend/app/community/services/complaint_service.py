from collections import Counter
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import utcnow
from app.common.enums import ComplaintStatus, UserRole
from app.community.models.complaint import Complaint
from app.community.repositories.complaint_repository import ComplaintRepository
from app.community.schemas.complaint import (
    ComplaintCreate,
    ComplaintEventResponse,
    ComplaintResponse,
    ComplaintStatsResponse,
    ComplaintStatusUpdate,
    PaginatedComplaintsResponse,
)
from app.core.exceptions import ForbiddenException, NotFoundException
from app.identity.models.user import User
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.property.repositories.property_repository import PropertyRepository

_RESOLVED_STATUSES = (ComplaintStatus.resolved.value, ComplaintStatus.rated.value)
_ALLOWED_TRANSITIONS = {
    ComplaintStatus.submitted.value: {ComplaintStatus.reviewed.value},
    ComplaintStatus.reviewed.value: {ComplaintStatus.assigned.value},
    ComplaintStatus.assigned.value: {ComplaintStatus.in_progress.value},
    ComplaintStatus.in_progress.value: {ComplaintStatus.resolved.value},
    ComplaintStatus.resolved.value: {ComplaintStatus.rated.value},
}


class ComplaintService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = ComplaintRepository(db)
        self._property_repo = PropertyRepository(db)
        self._estate_authorization = EstateAuthorizationService(db)

    # ---- helpers -------------------------------------------------------

    @staticmethod
    def _is_admin(user: User) -> bool:
        return user.role == UserRole.hoa_admin.value

    @staticmethod
    def _to_response(complaint: Complaint, viewer: User) -> ComplaintResponse:
        response = ComplaintResponse.model_validate(complaint)
        # anonymous complaints hide the author from everyone except the author
        if complaint.is_anonymous and complaint.user_id != viewer.user_id:
            response.user_id = None
        return response

    async def _get_or_404_in_estate(self, *, complaint_id: int, estate_id: int) -> Complaint:
        complaint = await self._repo.get_by_id_in_estate(
            complaint_id=complaint_id, estate_id=estate_id
        )
        if complaint is None:
            raise NotFoundException(f"Complaint with id {complaint_id} was not found.")
        return complaint

    # ---- use cases -----------------------------------------------------

    async def create_complaint(
        self, payload: ComplaintCreate, user: User, *, estate_id: int
    ) -> ComplaintResponse:
        await self._estate_authorization.require_membership(
            user_id=user.user_id, estate_id=estate_id
        )
        property_ = await self._property_repo.get_by_id_in_estate(
            unit_id=payload.unit_id, estate_id=estate_id
        )
        if property_ is None:
            raise NotFoundException(f"Property with id {payload.unit_id} was not found.")
        if not self._is_admin(user):
            membership = await self._estate_authorization.require_membership(
                user_id=user.user_id, estate_id=estate_id
            )
            if membership.property_id != payload.unit_id:
                raise ForbiddenException("You can only report issues for your assigned property.")
        complaint = await self._repo.create(
            user_id=user.user_id,
            unit_id=payload.unit_id,
            estate_id=estate_id,
            category=payload.category.strip(),
            description=payload.description.strip(),
            priority=payload.priority,
            is_anonymous=payload.is_anonymous,
        )
        return self._to_response(complaint, user)

    async def list_complaints(
        self,
        user: User,
        *,
        page: int,
        page_size: int,
        unit_id: int | None = None,
        status: str | None = None,
        category: str | None = None,
        estate_id: int,
    ) -> PaginatedComplaintsResponse:
        await self._estate_authorization.require_membership(
            user_id=user.user_id, estate_id=estate_id
        )
        # HOA admins see every complaint; everyone else only sees their own.
        scope_user_id = None if self._is_admin(user) else user.user_id
        filters = dict(
            user_id=scope_user_id,
            unit_id=unit_id,
            estate_id=estate_id,
            status=status,
            category=category,
        )
        complaints = await self._repo.search(
            offset=(page - 1) * page_size, limit=page_size, **filters
        )
        total = await self._repo.count(**filters)
        return PaginatedComplaintsResponse(
            count=total,
            page=page,
            page_size=page_size,
            complaints=[self._to_response(c, user) for c in complaints],
        )

    async def get_complaint(
        self, complaint_id: int, user: User, *, estate_id: int
    ) -> ComplaintResponse:
        await self._estate_authorization.require_membership(
            user_id=user.user_id, estate_id=estate_id
        )
        complaint = await self._get_or_404_in_estate(complaint_id=complaint_id, estate_id=estate_id)
        if not self._is_admin(user) and complaint.user_id != user.user_id:
            raise ForbiddenException("You can only view your own complaints.")
        return self._to_response(complaint, user)

    async def update_status(
        self, complaint_id: int, payload: ComplaintStatusUpdate, admin: User, *, estate_id: int
    ) -> ComplaintResponse:
        await self._estate_authorization.require_role(
            actor=admin, estate_id=estate_id, allowed_roles=(UserRole.hoa_admin.value,)
        )
        complaint = await self._get_or_404_in_estate(complaint_id=complaint_id, estate_id=estate_id)
        new_status = payload.status.value
        allowed = _ALLOWED_TRANSITIONS.get(complaint.status or "", set())
        if new_status not in allowed:
            raise ForbiddenException(
                f"Complaint cannot transition from {complaint.status} to {new_status}."
            )
        if new_status == ComplaintStatus.assigned.value and not payload.assigned_to:
            raise ForbiddenException("An assignee is required before a complaint can be assigned.")
        old_status = complaint.status or ComplaintStatus.submitted.value
        complaint.status = new_status
        if payload.assigned_to is not None:
            complaint.assigned_to = payload.assigned_to
        now = utcnow()
        if new_status == ComplaintStatus.reviewed.value:
            complaint.reviewed_at = now
        elif new_status == ComplaintStatus.assigned.value:
            complaint.assigned_at = now
        elif new_status == ComplaintStatus.in_progress.value:
            complaint.started_at = now
        elif new_status in _RESOLVED_STATUSES:
            if complaint.resolved_at is None:
                complaint.resolved_at = now
        complaint = await self._repo.record_transition(
            complaint=complaint,
            actor_user_id=admin.user_id,
            from_status=old_status,
            to_status=new_status,
            note=payload.note.strip() if payload.note else None,
        )
        return self._to_response(complaint, admin)

    async def list_events(
        self, complaint_id: int, user: User, *, estate_id: int
    ) -> list[ComplaintEventResponse]:
        await self.get_complaint(complaint_id, user, estate_id=estate_id)
        events = await self._repo.list_events(complaint_id=complaint_id)
        return [ComplaintEventResponse.model_validate(event) for event in events]

    async def get_stats(self, admin: User, *, estate_id: int) -> ComplaintStatsResponse:
        await self._estate_authorization.require_role(
            actor=admin, estate_id=estate_id, allowed_roles=(UserRole.hoa_admin.value,)
        )
        complaints = await self._repo.get_all(estate_id=estate_id)
        total = len(complaints)

        by_status = Counter(c.status for c in complaints)
        by_category = Counter(c.category for c in complaints)

        resolved = [c for c in complaints if c.status in _RESOLVED_STATUSES]
        resolution_rate_pct = (
            (Decimal(len(resolved)) / Decimal(total) * Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if total > 0
            else Decimal("0.00")
        )

        resolution_hours = [
            Decimal((c.resolved_at - c.created_at).total_seconds()) / Decimal(3600)
            for c in resolved
            if c.resolved_at is not None and c.created_at is not None
        ]
        avg_resolution_hours = (
            (sum(resolution_hours) / Decimal(len(resolution_hours))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if resolution_hours
            else None
        )

        return ComplaintStatsResponse(
            total=total,
            by_status=dict(by_status),
            by_category=dict(by_category),
            resolution_rate_pct=resolution_rate_pct,
            avg_resolution_hours=avg_resolution_hours,
        )
