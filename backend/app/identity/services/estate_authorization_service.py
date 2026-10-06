"""Application service for the estate tenant boundary."""
from collections.abc import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException
from app.identity.models.estate_membership import EstateMembership
from app.identity.models.user import User
from app.identity.repositories.estate_membership_repository import EstateMembershipRepository


class EstateAuthorizationService:
    """Checks persisted membership before an estate-scoped resource is loaded."""

    def __init__(self, db: AsyncSession) -> None:
        self._memberships = EstateMembershipRepository(db)

    async def require_membership(self, *, user_id: int, estate_id: int) -> EstateMembership:
        membership = await self._memberships.get_for_user_and_estate(
            user_id=user_id, estate_id=estate_id
        )
        if membership is None:
            raise ForbiddenException("You do not have access to this estate.")
        return membership

    async def require_role(
        self, *, actor: User, estate_id: int, allowed_roles: Iterable[str]
    ) -> EstateMembership:
        allowed = set(allowed_roles)
        membership = await self.require_membership(user_id=actor.user_id, estate_id=estate_id)
        if actor.role not in allowed or membership.membership_role not in allowed:
            raise ForbiddenException("Your estate membership does not permit this action.")
        return membership
