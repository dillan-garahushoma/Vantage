from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import Page
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
)
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.identity.models.user import User
from app.identity.services.estate_authorization_service import (
    EstateAccess,
    EstateAuthorizationService,
)
from app.property.repositories.property_repository import PropertyRepository


class ComplaintService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = ComplaintRepository(db)
        self._property_repo = PropertyRepository(db)
        self._estate_authorization = EstateAuthorizationService(db)

    # ---- helpers -------------------------------------------------------

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
        access = await self._estate_authorization.resolve_access(user, estate_id)
        property_ = await self._property_repo.get_by_id_in_estate(
            unit_id=payload.unit_id, estate_id=estate_id
        )
        if property_ is None:
            raise NotFoundException(f"Property with id {payload.unit_id} was not found.")
        if not access.is_estate_admin:
            if payload.unit_id not in access.property_ids:
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
        size: int,
        sort: str = "-created_at",
        unit_id: int | None = None,
        status: str | None = None,
        category: str | None = None,
        estate_id: int,
    ) -> Page[ComplaintResponse]:
        access = await self._estate_authorization.resolve_access(user, estate_id)
        # HOA admins see every complaint; everyone else only sees their own.
        scope_user_id = None if access.is_estate_admin else user.user_id
        filters = dict(
            user_id=scope_user_id,
            unit_id=unit_id,
            estate_id=estate_id,
            status=status,
            category=category,
        )
        complaints = await self._repo.search(
            offset=(page - 1) * size, limit=size, sort=sort, **filters
        )
        total = await self._repo.count(**filters)
        return Page[ComplaintResponse](
            items=[self._to_response(c, user) for c in complaints],
            total=total,
            page=page,
            size=size,
        )

    async def get_complaint(
        self, complaint_id: int, user: User, *, estate_id: int
    ) -> ComplaintResponse:
        access = await self._estate_authorization.resolve_access(user, estate_id)
        complaint = await self._get_or_404_in_estate(complaint_id=complaint_id, estate_id=estate_id)
        if not access.is_estate_admin and complaint.user_id != user.user_id:
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
        # Enforce C4 and B6: only submitted -> reviewed allowed through this endpoint
        if (
            new_status != ComplaintStatus.reviewed.value
            or complaint.status != ComplaintStatus.submitted.value
        ):
            raise ConflictException(
                f"Complaint cannot transition from {complaint.status} to {new_status}."
            )
        old_status = complaint.status or ComplaintStatus.submitted.value
        complaint.status = new_status
        now = utcnow()
        complaint.reviewed_at = now
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
        access = await self._estate_authorization.resolve_access(user, estate_id)
        complaint = await self._get_or_404_in_estate(complaint_id=complaint_id, estate_id=estate_id)
        if not access.is_estate_admin and complaint.user_id != user.user_id:
            raise ForbiddenException("You can only view your own complaints.")

        events = await self._repo.list_events(complaint_id=complaint_id)
        is_anon = bool(complaint.is_anonymous)
        event_responses = []
        for event in events:
            evt_resp = ComplaintEventResponse.model_validate(event)
            if is_anon and user.user_id != complaint.user_id:
                if evt_resp.actor_user_id == complaint.user_id:
                    evt_resp.actor_user_id = None
            event_responses.append(evt_resp)
        return event_responses

    async def get_stats(self, admin: User, *, estate_id: int) -> ComplaintStatsResponse:
        await self._estate_authorization.require_role(
            actor=admin, estate_id=estate_id, allowed_roles=(UserRole.hoa_admin.value,)
        )
        stats = await self._repo.get_stats_aggregates(estate_id=estate_id)
        return ComplaintStatsResponse(**stats)
