from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import utcnow
from app.identity.models.provider_invitation import ProviderInvitation


class ProviderInvitationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def revoke_active_for_email(self, *, estate_id: int, email: str) -> None:
        await self._db.execute(
            update(ProviderInvitation)
            .where(
                ProviderInvitation.estate_id == estate_id,
                ProviderInvitation.email == email,
                ProviderInvitation.accepted_at.is_(None),
                ProviderInvitation.revoked_at.is_(None),
            )
            .values(revoked_at=utcnow())
        )
        await self._db.flush()

    async def add(self, **fields: object) -> ProviderInvitation:
        invitation = ProviderInvitation(**fields)
        self._db.add(invitation)
        await self._db.flush()
        return invitation

    async def get_by_token_digest_for_update(
        self, *, token_digest: str
    ) -> ProviderInvitation | None:
        result = await self._db.execute(
            select(ProviderInvitation)
            .where(ProviderInvitation.token_digest == token_digest)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def mark_accepted(
        self, invitation: ProviderInvitation, *, accepted_at: datetime
    ) -> None:
        invitation.accepted_at = accepted_at
        await self._db.flush()
