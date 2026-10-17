"""Application service for estate membership: joining, listing and removal.

Joining is deliberately self-service and immediate. There is no per-resident
approval step: possession of the estate's live join code *and* a unit number that
exists inside that estate is the whole proof required, because the estate admin is
the one who chose to share the code. Removing a member is an admin action and
never touches the person's account, their complaints or the history of what
happened.
"""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import utcnow
from app.common.enums import UserRole
from app.common.pagination import Page
from app.common.validators import normalise_email
from app.core.exceptions import ConflictException, NotFoundException
from app.identity.domain.join_code import normalise_join_code
from app.identity.models.user import User
from app.identity.repositories.estate_join_code_repository import EstateJoinCodeRepository
from app.identity.repositories.estate_membership_event_repository import (
    EstateMembershipEventRepository,
)
from app.identity.repositories.estate_membership_repository import EstateMembershipRepository
from app.identity.repositories.user_repository import UserRepository
from app.identity.schemas.membership import (
    MembershipJoinRequest,
    MembershipJoinResponse,
    MembershipResponse,
)
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.identity.services.join_attempt_limiter import JoinAttemptLimiter, join_attempt_limiter
from app.property.repositories.estate_repository import EstateRepository
from app.property.repositories.property_repository import PropertyRepository
from app.providers.repositories.service_provider_repository import ServiceProviderRepository

# One uniform refusal for every unusable code, so a caller cannot tell an unknown
# code from an expired one from a revoked one.
INVALID_CODE_MESSAGE = "That code is not valid."

# One uniform refusal for every unusable provider lookup, so an admin cannot use
# this endpoint to discover which email addresses have accounts.
PROVIDER_NOT_AVAILABLE_MESSAGE = (
    "No registered service provider with that email address can be added to this estate."
)

PROVIDER_LOOKUP_RATE_LIMIT_MESSAGE = (
    "Too many unsuccessful service-provider lookups. Please try again later."
)

# Rows an admin may remove. An admin membership is not removable through the API:
# an estate with no admin would be unreachable.
REMOVABLE_MEMBERSHIP_ROLES = frozenset(
    {UserRole.resident.value, UserRole.service_provider.value}
)


class MembershipService:
    def __init__(self, db: AsyncSession, *, limiter: JoinAttemptLimiter | None = None) -> None:
        self._db = db
        self._memberships = EstateMembershipRepository(db)
        self._codes = EstateJoinCodeRepository(db)
        self._events = EstateMembershipEventRepository(db)
        self._estates = EstateRepository(db)
        self._properties = PropertyRepository(db)
        self._users = UserRepository(db)
        self._providers = ServiceProviderRepository(db)
        self._estate_authorization = EstateAuthorizationService(db)
        # The ONB-2 limiter is reused rather than duplicated: it is keyed by user
        # id, and an account is either a resident (who redeems codes) or an HOA
        # admin (who looks providers up by email), so the two never share a
        # counter in practice. Failed lookups count exactly like failed codes.
        self._limiter = limiter if limiter is not None else join_attempt_limiter

    # ---- resident self-service ------------------------------------------

    async def join_with_code(
        self, actor: User, payload: MembershipJoinRequest
    ) -> MembershipJoinResponse:
        """Redeem a join code for one unit, with no approval step.

        The estate is taken from the code row, never from the request: a resident
        cannot name the estate they want to join any more than they can name the
        unit they want to claim outside it.
        """
        self._limiter.ensure_allowed(actor.user_id)

        code = normalise_join_code(payload.code)
        unit_no = payload.unit_no.strip()
        now = utcnow()

        row = await self._codes.get_by_code(code) if code else None
        unusable = row is None or row.revoked_at is not None
        if not unusable and row.expires_at is not None and row.expires_at <= now:
            unusable = True
        if unusable:
            # Any unusable code counts against the limiter, so guessing is what
            # gets throttled rather than what gets rewarded.
            self._limiter.record_failure(actor.user_id)
            raise NotFoundException(INVALID_CODE_MESSAGE)

        estate_id = row.estate_id

        unit = await self._properties.get_by_unit_no_in_estate_ci(
            estate_id=estate_id, unit_no=unit_no
        )
        if unit is None:
            raise NotFoundException(
                f"Unit {unit_no} was not found in this estate. "
                "Check the number with your estate office."
            )

        if (
            await self._memberships.get_for_user_and_estate(
                user_id=actor.user_id, estate_id=estate_id
            )
            is not None
        ):
            raise ConflictException("You are already a member of this estate.")

        try:
            await self._memberships.add(
                user_id=actor.user_id,
                estate_id=estate_id,
                property_id=unit.unit_id,
                membership_role=UserRole.resident.value,
                join_code_id=row.code_id,
            )
            await self._events.record(
                estate_id=estate_id,
                user_id=actor.user_id,
                membership_role=UserRole.resident.value,
                property_id=unit.unit_id,
                event_type="joined",
                actor_user_id=actor.user_id,
            )
            # The membership and its audit event are one transaction.
            await self._db.commit()
        except IntegrityError:
            # A concurrent duplicate join lost the race against
            # uq_membership_user_estate_join. That is a conflict, not a crash.
            await self._db.rollback()
            raise ConflictException("You are already a member of this estate.")

        estate = await self._estates.get_by_id(estate_id)
        return MembershipJoinResponse(
            estate_id=estate_id,
            estate_name=estate.name if estate is not None else "",
            unit_id=unit.unit_id,
            unit_no=unit.unit_no,
            role=UserRole.resident.value,
        )

    # ---- admin: add an already-registered provider -----------------------

    async def add_provider_by_email(
        self, actor: User, *, estate_id: int, email: str
    ) -> MembershipResponse:
        """Bind a registered service provider to this estate, one transaction.

        The provider must already have an account with the ``service_provider``
        role *and* a linked provider profile: an admin adds somebody who has
        registered themselves, it does not create accounts. Anything that does
        not match - unknown email, a resident's email, a provider account with
        no profile - is the same 404, and it is counted against the same
        limiter that throttles join-code guessing, because otherwise this
        endpoint is an email-enumeration oracle hand-held by an admin.
        """
        await self._require_estate_admin(actor, estate_id)
        self._limiter.ensure_allowed(
            actor.user_id, message=PROVIDER_LOOKUP_RATE_LIMIT_MESSAGE
        )

        normalised = normalise_email(email)
        user = await self._users.get_by_email(normalised)
        provider = (
            await self._providers.get_by_user_id(user.user_id) if user is not None else None
        )
        eligible = (
            user is not None
            and user.role == UserRole.service_provider.value
            and provider is not None
        )
        if not eligible:
            self._limiter.record_failure(actor.user_id)
            raise NotFoundException(PROVIDER_NOT_AVAILABLE_MESSAGE)
        assert user is not None

        existing = await self._memberships.get_for_user_and_estate(
            user_id=user.user_id, estate_id=estate_id
        )
        if existing is not None:
            raise ConflictException("That service provider is already a member of this estate.")

        try:
            membership = await self._memberships.add(
                user_id=user.user_id,
                estate_id=estate_id,
                property_id=None,
                membership_role=UserRole.service_provider.value,
            )
            await self._events.record(
                estate_id=estate_id,
                user_id=user.user_id,
                membership_role=UserRole.service_provider.value,
                property_id=None,
                event_type="joined",
                actor_user_id=actor.user_id,
            )
            # The membership and its audit event are one transaction.
            await self._db.commit()
            await self._db.refresh(membership)
        except IntegrityError:
            # uq_estate_memberships_user_estate_null_property: a concurrent add
            # lost the race. That is a conflict, not a crash.
            await self._db.rollback()
            raise ConflictException("That service provider is already a member of this estate.")

        # A successful lookup clears the admin's failure window.
        self._limiter.reset(actor.user_id)
        return MembershipResponse(
            membership_id=membership.membership_id,
            role=membership.membership_role,
            full_name=user.full_name,
            email=user.email,
            unit_no=None,
            joined_at=membership.created_at,
        )

    # ---- admin member management ----------------------------------------

    async def _require_estate_admin(self, actor: User, estate_id: int) -> None:
        await self._estate_authorization.require_role(
            actor=actor,
            estate_id=estate_id,
            allowed_roles=(UserRole.hoa_admin.value,),
        )

    async def list_members(
        self,
        actor: User,
        *,
        estate_id: int,
        role: str | None,
        page: int,
        page_size: int,
    ) -> Page[MembershipResponse]:
        """One page of this estate's members, newest first."""
        await self._require_estate_admin(actor, estate_id)
        rows = await self._memberships.list_members_for_estate(
            estate_id=estate_id,
            role=role,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        total = await self._memberships.count_members_for_estate(
            estate_id=estate_id, role=role
        )
        return Page[MembershipResponse](
            items=[
                MembershipResponse(
                    membership_id=row.membership_id,
                    role=row.membership_role,
                    full_name=row.full_name,
                    email=row.email,
                    unit_no=row.unit_no,
                    joined_at=row.created_at,
                )
                for row in rows
            ],
            total=total,
            page=page,
            size=page_size,
        )

    async def remove_member(self, actor: User, *, membership_id: int, estate_id: int) -> None:
        """Remove one resident or provider membership, with an audit event.

        Only the membership goes: the user account, their complaints and every
        event already written stay exactly where they are, which is what
        ``/auth/estates`` then reflects on the next call.
        """
        await self._require_estate_admin(actor, estate_id)

        membership = await self._memberships.get_by_id_in_estate(
            membership_id=membership_id, estate_id=estate_id
        )
        if membership is None:
            raise NotFoundException(f"Membership with id {membership_id} was not found.")

        if membership.membership_role not in REMOVABLE_MEMBERSHIP_ROLES:
            raise ConflictException(
                "An estate administrator's membership cannot be removed here."
            )

        try:
            await self._events.record(
                estate_id=estate_id,
                user_id=membership.user_id,
                membership_role=membership.membership_role,
                property_id=membership.property_id,
                event_type="removed",
                actor_user_id=actor.user_id,
            )
            await self._memberships.delete(membership)
            await self._db.commit()
        except IntegrityError:  # pragma: no cover - nothing here can conflict today
            await self._db.rollback()
            raise ConflictException("The membership could not be removed.")


__all__ = ["MembershipService", "INVALID_CODE_MESSAGE"]
