"""Application service for the estate tenant boundary."""
from collections.abc import Iterable
from dataclasses import dataclass
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.core.exceptions import ForbiddenException
from app.identity.models.user import User
from app.identity.repositories.estate_membership_repository import EstateMembershipRepository
from app.property.repositories.estate_repository import EstateRepository


@dataclass(frozen=True)
class EstateAccessSummary:
    """A read-only view of one estate a user can act inside."""

    estate_id: int
    estate_name: str
    suburb: str
    city: str
    province: str
    membership_roles: frozenset[str]
    property_ids: frozenset[int]
    is_estate_admin: bool
    is_estate_provider: bool
    is_demo: bool = False


@dataclass(frozen=True)
class EstateAccess:
    user_id: int
    estate_id: int
    membership_roles: frozenset[str]
    property_ids: frozenset[int]
    is_estate_admin: bool
    is_estate_provider: bool

    @property
    def membership_role(self) -> str | None:
        return next(iter(self.membership_roles), None)

    @property
    def property_id(self) -> int | None:
        return next(iter(self.property_ids), None)


class EstateAuthorizationService:
    """Checks persisted membership before an estate-scoped resource is loaded."""

    def __init__(self, db: AsyncSession) -> None:
        self._memberships = EstateMembershipRepository(db)
        self._estates = EstateRepository(db)

    async def list_accessible_estates(self, actor: User | object) -> list[EstateAccessSummary]:
        """List the estates the actor may select, newest-safe and server-resolved.

        The client never supplies an ``estate_id``; this is the only source of
        truth for which estates a user may act in. A user still awaiting HOA
        provisioning gets an empty list.
        """
        user_id = actor.user_id if hasattr(actor, "user_id") else int(actor)
        user_role = getattr(actor, "role", "")

        memberships = await self._memberships.list_for_user(user_id=user_id)
        if not memberships:
            return []

        estate_ids = sorted({m.estate_id for m in memberships if m.estate_id is not None})
        estates = await self._estates.get_many_by_ids(estate_ids)

        grouped: dict[int, dict[str, set]] = {}
        for membership in memberships:
            if membership.estate_id is None or membership.estate_id not in estates:
                continue
            bucket = grouped.setdefault(
                membership.estate_id, {"roles": set(), "properties": set()}
            )
            if membership.membership_role is not None:
                bucket["roles"].add(membership.membership_role)
            if membership.property_id is not None:
                bucket["properties"].add(membership.property_id)

        summaries = [
            EstateAccessSummary(
                estate_id=estate_id,
                estate_name=estates[estate_id].name,
                suburb=estates[estate_id].suburb,
                city=estates[estate_id].city,
                province=estates[estate_id].province,
                membership_roles=frozenset(bucket["roles"]),
                property_ids=frozenset(bucket["properties"]),
                is_estate_admin=bool(
                    user_role == UserRole.hoa_admin.value
                    and UserRole.hoa_admin.value in bucket["roles"]
                ),
                is_estate_provider=bool(
                    user_role == UserRole.service_provider.value
                    and UserRole.service_provider.value in bucket["roles"]
                ),
                # A seeded demonstration estate; never real customer data.
                is_demo=bool(getattr(estates[estate_id], "is_demo", False)),
            )
            for estate_id, bucket in grouped.items()
        ]
        summaries.sort(key=lambda s: s.estate_name.lower())
        return summaries

    async def has_membership_role_in_any_estate(
        self, *, user_id: int, membership_role: str
    ) -> bool:
        return await self._memberships.has_membership_role_for_user(
            user_id=user_id, membership_role=membership_role
        )

    async def resolve_access(self, actor: User | object, estate_id: int) -> EstateAccess:
        user_id = actor.user_id if hasattr(actor, "user_id") else int(actor)
        user_role = getattr(actor, "role", "")

        if hasattr(self._memberships, "list_for_user_and_estate"):
            memberships = await self._memberships.list_for_user_and_estate(
                user_id=user_id, estate_id=estate_id
            )
        else:
            m = await self._memberships.get_for_user_and_estate(
                user_id=user_id, estate_id=estate_id
            )
            memberships = [m] if m is not None else []

        if not isinstance(memberships, (list, tuple)):
            memberships = [memberships] if memberships is not None else []

        if not memberships:
            raise ForbiddenException("You do not have access to this estate.")

        roles = frozenset(
            m.membership_role for m in memberships if getattr(m, "membership_role", None) is not None
        )
        property_ids = frozenset(
            m.property_id for m in memberships if getattr(m, "property_id", None) is not None
        )
        is_admin = bool(
            user_role == UserRole.hoa_admin.value and UserRole.hoa_admin.value in roles
        )
        is_provider = bool(
            user_role == UserRole.service_provider.value and UserRole.service_provider.value in roles
        )

        return EstateAccess(
            user_id=user_id,
            estate_id=estate_id,
            membership_roles=roles,
            property_ids=property_ids,
            is_estate_admin=is_admin,
            is_estate_provider=is_provider,
        )

    async def require_membership(
        self, *, user_id: int | None = None, actor: User | None = None, estate_id: int
    ) -> EstateAccess:
        effective_actor = (
            actor if actor is not None else SimpleNamespace(user_id=user_id, role="")
        )
        return await self.resolve_access(effective_actor, estate_id)

    async def require_role(
        self, *, actor: User, estate_id: int, allowed_roles: Iterable[str]
    ) -> EstateAccess:
        access = await self.resolve_access(actor, estate_id)
        allowed = set(allowed_roles)
        if actor.role not in allowed or not (access.membership_roles & allowed):
            raise ForbiddenException("Your estate membership does not permit this action.")
        return access
