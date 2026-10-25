"""Application service for resident registration requests.

This is the approval-based path onto an estate, and it sits *beside* the join-code
path rather than replacing it: a resident may either redeem a code the estate office
handed them (immediate, self-service) or submit a request here and wait for an
administrator to decide it. Both produce the same kind of membership row, so
everything downstream is unchanged.

The rules this service owns:

* **A resident requests; an administrator decides.** Submitting never grants
  access. Only :meth:`approve` writes a membership, and it is gated on an
  ``hoa_admin`` membership of the *same* estate, re-resolved server-side.
* **Self-approval is impossible** because the actor who creates a request is a
  resident and the actor who decides it must be an estate administrator; the two
  roles do not overlap in this product.
* **A decision is idempotent under concurrency.** The request is read
  ``FOR UPDATE``; whoever loses the race reads a non-pending status and is refused
  with a 409 rather than overwriting the first decision.
* **One pending request per resident per estate** (a partial unique index), so a
  resident cannot queue duplicates, and a decided request is never deleted: it is
  the estate's record of who was admitted, by whom and when.

Notification is deliberately *outside* the business transaction: the request is
committed first, then a best-effort email is attempted, and only a successful send
stamps its idempotence timestamp. A relay outage therefore leaves the request in
the admin queue - which is the durable source of truth - instead of losing it.
"""
from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import utcnow
from app.common.enums import ResidencyRequestStatus, UserRole
from app.common.pagination import Page
from app.core.config import get_settings
from app.core.exceptions import ConflictException, NotFoundException
from app.identity.models.estate_residency_request import EstateResidencyRequest
from app.identity.models.user import User
from app.identity.repositories.estate_membership_event_repository import (
    EstateMembershipEventRepository,
)
from app.identity.repositories.estate_membership_repository import EstateMembershipRepository
from app.identity.repositories.estate_residency_request_repository import (
    EstateResidencyRequestRepository,
)
from app.identity.schemas.residency_request import (
    ResidencyRequestCreate,
    ResidencyRequestResponse,
)
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.identity.services.join_attempt_limiter import JoinAttemptLimiter, join_attempt_limiter
from app.notifications.email import build_email_sender
from app.notifications.residency_notifications import ResidencyNotifier
from app.property.repositories.estate_repository import EstateRepository
from app.property.repositories.property_repository import PropertyRepository

logger = logging.getLogger(__name__)

# One uniform refusal for an estate that does not exist, so a caller cannot map
# the estate table by walking ids.
ESTATE_NOT_FOUND_MESSAGE = "That complex was not found."

# A unit that is not in the estate is a different, actionable message; it is
# counted against the same limiter that throttles code guessing, so unit-number
# probing is not free.
UNIT_NOT_FOUND_TEMPLATE = (
    "Unit {unit_no} was not found in this complex. Check the number with your estate office."
)

ALREADY_MEMBER_MESSAGE = "You are already a member of this estate."
DUPLICATE_PENDING_MESSAGE = (
    "You already have a registration awaiting review for this estate."
)
REQUEST_NOT_FOUND_TEMPLATE = "Residency request with id {request_id} was not found."
ALREADY_DECIDED_MESSAGE = "That request has already been decided."
APPLICANT_GONE_MESSAGE = (
    "The applicant's account no longer exists, so this request cannot be approved."
)


class ResidencyRequestService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        notifier: ResidencyNotifier | None = None,
        limiter: JoinAttemptLimiter | None = None,
        base_url: str | None = None,
    ) -> None:
        self._db = db
        self._requests = EstateResidencyRequestRepository(db)
        self._memberships = EstateMembershipRepository(db)
        self._events = EstateMembershipEventRepository(db)
        self._estates = EstateRepository(db)
        self._properties = PropertyRepository(db)
        self._authorization = EstateAuthorizationService(db)
        self._limiter = limiter if limiter is not None else join_attempt_limiter
        if notifier is not None:
            self._notifier = notifier
        else:
            settings = get_settings()
            self._notifier = ResidencyNotifier(
                db,
                sender=build_email_sender(settings),
                base_url=base_url if base_url is not None else settings.APP_BASE_URL,
            )

    # ---- resident: submit and read own ----------------------------------

    async def submit(
        self, actor: User, payload: ResidencyRequestCreate
    ) -> ResidencyRequestResponse:
        """Record one pending request. No access is granted here."""
        self._limiter.ensure_allowed(actor.user_id)

        estate = await self._estates.get_by_id(payload.estate_id)
        if estate is None:
            self._limiter.record_failure(actor.user_id)
            raise NotFoundException(ESTATE_NOT_FOUND_MESSAGE)

        unit = None
        if payload.unit_no is not None:
            unit = await self._properties.get_by_unit_no_in_estate_ci(
                estate_id=payload.estate_id, unit_no=payload.unit_no
            )
            if unit is None:
                self._limiter.record_failure(actor.user_id)
                raise NotFoundException(
                    UNIT_NOT_FOUND_TEMPLATE.format(unit_no=payload.unit_no)
                )

        if (
            await self._memberships.get_for_user_and_estate(
                user_id=actor.user_id, estate_id=payload.estate_id
            )
            is not None
        ):
            raise ConflictException(ALREADY_MEMBER_MESSAGE)

        if (
            await self._requests.get_pending_for_user_and_estate(
                user_id=actor.user_id, estate_id=payload.estate_id
            )
            is not None
        ):
            raise ConflictException(DUPLICATE_PENDING_MESSAGE)

        try:
            request = await self._requests.add(
                estate_id=payload.estate_id,
                user_id=actor.user_id,
                property_id=unit.unit_id if unit is not None else None,
                unit_no=unit.unit_no if unit is not None else None,
                status=ResidencyRequestStatus.pending.value,
                applicant_name=actor.full_name,
                applicant_email=actor.email,
                applicant_phone=getattr(actor, "phoneno", None),
                note=payload.note,
            )
            # The business state is one transaction and it commits before any
            # email is attempted.
            await self._db.commit()
            await self._db.refresh(request)
        except IntegrityError:
            # uq_estate_residency_requests_one_pending_per_user_estate: a
            # concurrent duplicate submission lost the race. That is a conflict.
            await self._db.rollback()
            raise ConflictException(DUPLICATE_PENDING_MESSAGE)

        # A valid submission clears the caller's failure window.
        self._limiter.reset(actor.user_id)
        await self._deliver_creation_notice(request, estate_name=estate.name)
        return self._to_response(request, estate_name=estate.name)

    async def list_mine(self, actor: User) -> list[ResidencyRequestResponse]:
        """Every request this person has submitted, newest first."""
        rows = await self._requests.list_for_user(user_id=actor.user_id)
        names = await self._estate_names({row.estate_id for row in rows})
        return [self._to_response(row, estate_name=names.get(row.estate_id)) for row in rows]

    # ---- administrator: the queue and the decisions ----------------------

    async def pending_count(self, actor: User, *, estate_id: int) -> int:
        await self._require_estate_admin(actor, estate_id)
        return await self._requests.count_pending_for_estate(estate_id=estate_id)

    async def list_for_estate(
        self,
        actor: User,
        *,
        estate_id: int,
        status: str | None,
        search: str | None,
        page: int,
        page_size: int,
    ) -> Page[ResidencyRequestResponse]:
        """One page of the estate's requests, newest first, filterable."""
        await self._require_estate_admin(actor, estate_id)
        rows = await self._requests.list_for_estate(
            estate_id=estate_id,
            status=status,
            search=search,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        total = await self._requests.count_for_estate(
            estate_id=estate_id, status=status, search=search
        )
        return Page[ResidencyRequestResponse](
            items=[self._to_response(row) for row in rows],
            total=total,
            page=page,
            size=page_size,
        )

    async def approve(
        self, actor: User, *, estate_id: int, request_id: int
    ) -> ResidencyRequestResponse:
        """Approve a pending request and grant the resident's membership.

        The membership, its audit event and the request's decided status are one
        transaction and one commit. If the applicant is somehow already a member
        (they redeemed a code while waiting), the request is still approved but no
        second membership is created.
        """
        await self._require_estate_admin(actor, estate_id)
        request = await self._requests.get_by_id_in_estate(
            request_id=request_id, estate_id=estate_id, for_update=True
        )
        if request is None:
            raise NotFoundException(REQUEST_NOT_FOUND_TEMPLATE.format(request_id=request_id))
        if request.status != ResidencyRequestStatus.pending.value:
            raise ConflictException(ALREADY_DECIDED_MESSAGE)
        if request.user_id is None:
            raise ConflictException(APPLICANT_GONE_MESSAGE)

        existing = await self._memberships.get_for_user_and_estate(
            user_id=request.user_id, estate_id=estate_id
        )
        try:
            if existing is None:
                await self._memberships.add(
                    user_id=request.user_id,
                    estate_id=estate_id,
                    property_id=request.property_id,
                    membership_role=UserRole.resident.value,
                )
                await self._events.record(
                    estate_id=estate_id,
                    user_id=request.user_id,
                    membership_role=UserRole.resident.value,
                    property_id=request.property_id,
                    event_type="joined",
                    actor_user_id=actor.user_id,
                )
            request.status = ResidencyRequestStatus.approved.value
            request.decided_by = actor.user_id
            request.decided_at = utcnow()
            await self._requests.save(request)
            await self._db.commit()
            await self._db.refresh(request)
        except IntegrityError:
            await self._db.rollback()
            raise ConflictException(ALREADY_DECIDED_MESSAGE)

        logger.info(
            "residency request approved (estate_id=%s request_id=%s by=%s)",
            estate_id,
            request.request_id,
            actor.user_id,
        )
        await self._deliver_decision(request, estate_id=estate_id)
        return self._to_response(request)

    async def reject(
        self,
        actor: User,
        *,
        estate_id: int,
        request_id: int,
        note: str | None = None,
    ) -> ResidencyRequestResponse:
        """Decline a pending request. No membership is ever created."""
        await self._require_estate_admin(actor, estate_id)
        request = await self._requests.get_by_id_in_estate(
            request_id=request_id, estate_id=estate_id, for_update=True
        )
        if request is None:
            raise NotFoundException(REQUEST_NOT_FOUND_TEMPLATE.format(request_id=request_id))
        if request.status != ResidencyRequestStatus.pending.value:
            raise ConflictException(ALREADY_DECIDED_MESSAGE)

        request.status = ResidencyRequestStatus.rejected.value
        request.decided_by = actor.user_id
        request.decided_at = utcnow()
        request.decision_note = note or None
        await self._requests.save(request)
        await self._db.commit()
        await self._db.refresh(request)

        logger.info(
            "residency request rejected (estate_id=%s request_id=%s by=%s)",
            estate_id,
            request.request_id,
            actor.user_id,
        )
        await self._deliver_decision(request, estate_id=estate_id)
        return self._to_response(request)

    # ---- helpers ---------------------------------------------------------

    async def _require_estate_admin(self, actor: User, estate_id: int) -> None:
        await self._authorization.require_role(
            actor=actor,
            estate_id=estate_id,
            allowed_roles=(UserRole.hoa_admin.value,),
        )

    async def _estate_names(self, estate_ids: set[int]) -> dict[int, str]:
        if not estate_ids:
            return {}
        rows = await self._estates.get_many_by_ids(sorted(estate_ids))
        return {estate_id: estate.name for estate_id, estate in rows.items()}

    async def _deliver_creation_notice(
        self, request: EstateResidencyRequest, *, estate_name: str
    ) -> None:
        """Best-effort HOA notification; never raises, never fails the request."""
        if request.notified_at is not None:
            return
        delivered = await self._notifier.notify_new_request(
            estate_name=estate_name, request=request
        )
        if delivered:
            request.notified_at = utcnow()
            await self._requests.save(request)
            await self._db.commit()

    async def _deliver_decision(
        self, request: EstateResidencyRequest, *, estate_id: int
    ) -> None:
        """Best-effort decision email to the applicant; never raises."""
        if request.decision_notified_at is not None:
            return
        names = await self._estate_names({estate_id})
        delivered = await self._notifier.notify_decision(
            estate_name=names.get(estate_id, "your estate"), request=request
        )
        if delivered:
            request.decision_notified_at = utcnow()
            await self._requests.save(request)
            await self._db.commit()

    @staticmethod
    def _to_response(
        request: EstateResidencyRequest, *, estate_name: str | None = None
    ) -> ResidencyRequestResponse:
        return ResidencyRequestResponse(
            request_id=request.request_id,
            estate_id=request.estate_id,
            estate_name=estate_name,
            unit_no=request.unit_no,
            status=request.status,
            applicant_name=request.applicant_name,
            applicant_email=request.applicant_email,
            applicant_phone=request.applicant_phone,
            note=request.note,
            created_at=request.created_at,
            decided_at=request.decided_at,
            decision_note=request.decision_note,
        )


__all__ = ["ResidencyRequestService"]
