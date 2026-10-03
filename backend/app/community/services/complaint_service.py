from collections import Counter
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import utcnow
from app.common.enums import ComplaintStatus, UserRole
from app.community.models.complaint import Complaint
from app.community.repositories.complaint_repository import ComplaintRepository
from app.community.schemas.complaint import (
    ComplaintCreate,
    ComplaintResponse,
    ComplaintStatsResponse,
    ComplaintStatusUpdate,
    PaginatedComplaintsResponse,
)
from app.core.exceptions import ForbiddenException, NotFoundException
from app.identity.models.user import User
from app.property.repositories.property_repository import PropertyRepository

_RESOLVED_STATUSES = (ComplaintStatus.resolved.value, ComplaintStatus.closed.value)


class ComplaintService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = ComplaintRepository(db)
        self._property_repo = PropertyRepository(db)

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

    async def _get_or_404(self, complaint_id: int) -> Complaint:
        complaint = await self._repo.get_by_id(complaint_id)
        if complaint is None:
            raise NotFoundException(f"Complaint with id {complaint_id} was not found.")
        return complaint

    # ---- use cases -----------------------------------------------------

    async def create_complaint(self, payload: ComplaintCreate, user: User) -> ComplaintResponse:
        if await self._property_repo.get_by_id(payload.unit_id) is None:
            raise NotFoundException(f"Property with id {payload.unit_id} was not found.")
        complaint = await self._repo.create(
            user_id=user.user_id,
            unit_id=payload.unit_id,
            category=payload.category.strip(),
            description=payload.description.strip(),
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
    ) -> PaginatedComplaintsResponse:
        # HOA admins see every complaint; everyone else only sees their own
        scope_user_id = None if self._is_admin(user) else user.user_id
        filters = dict(user_id=scope_user_id, unit_id=unit_id, status=status, category=category)
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

    async def get_complaint(self, complaint_id: int, user: User) -> ComplaintResponse:
        complaint = await self._get_or_404(complaint_id)
        if not self._is_admin(user) and complaint.user_id != user.user_id:
            raise ForbiddenException("You can only view your own complaints.")
        return self._to_response(complaint, user)

    async def update_status(
        self, complaint_id: int, payload: ComplaintStatusUpdate, admin: User
    ) -> ComplaintResponse:
        complaint = await self._get_or_404(complaint_id)
        new_status = payload.status.value
        complaint.status = new_status
        if payload.assigned_to is not None:
            complaint.assigned_to = payload.assigned_to
        if new_status in _RESOLVED_STATUSES:
            if complaint.resolved_at is None:
                complaint.resolved_at = utcnow()
        else:
            complaint.resolved_at = None
        complaint = await self._repo.save(complaint)
        return self._to_response(complaint, admin)

    async def get_stats(self) -> ComplaintStatsResponse:
        complaints = await self._repo.get_all()
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
