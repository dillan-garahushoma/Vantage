"""The estate's own profile: description and the two publish switches.

* **Read**: any member of the estate (``require_membership``), because the profile
  is the estate's own information and a resident should be able to see what their
  complex looks like to the public.
* **Write**: an ``hoa_admin`` *membership of that estate*. Every field is
  explicitly optional so a PATCH can send one switch, and ``extra="forbid"`` on
  the DTO means a ``name`` (or anything else) is rejected rather than ignored.

Why the two switches are separate decisions: ``is_public`` puts the estate in the
directory the whole internet can read; ``show_living_score`` publishes the number
derived from its complaints, incidents and maintenance. An estate may reasonably
want the first without the second, so they default to false independently.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.core.exceptions import NotFoundException
from app.identity.models.user import User
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.property.repositories.estate_repository import EstateRepository
from app.property.schemas.estate_profile import EstateProfileResponse, EstateProfileUpdate


class EstateProfileService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._estates = EstateRepository(db)
        self._authorization = EstateAuthorizationService(db)

    async def get_profile(self, actor: User, *, estate_id: int) -> EstateProfileResponse:
        """The estate profile, readable by any member of it."""
        await self._authorization.require_membership(actor=actor, estate_id=estate_id)
        estate = await self._estates.get_by_id(estate_id)
        if estate is None:
            raise NotFoundException(f"Estate with id {estate_id} was not found.")
        return EstateProfileResponse.model_validate(estate)

    async def update_profile(
        self, actor: User, *, estate_id: int, payload: EstateProfileUpdate
    ) -> EstateProfileResponse:
        """Change the description and/or the publish switches, once."""
        await self._authorization.require_role(
            actor=actor,
            estate_id=estate_id,
            allowed_roles=(UserRole.hoa_admin.value,),
        )
        estate = await self._estates.get_by_id(estate_id)
        if estate is None:
            raise NotFoundException(f"Estate with id {estate_id} was not found.")

        changes = payload.model_dump(exclude_unset=True)
        if "description" in changes and isinstance(changes["description"], str):
            changes["description"] = changes["description"].strip() or None
        for field, value in changes.items():
            setattr(estate, field, value)
        await self._db.commit()
        await self._db.refresh(estate)
        return EstateProfileResponse.model_validate(estate)
