"""Persistence for estate join codes.

Repositories flush, they never commit: the service owns the single commit for a
multi-step use case (see the architecture rules).
"""
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.models.estate_join_code import EstateJoinCode


class EstateJoinCodeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_code(self, code: str) -> EstateJoinCode | None:
        """Fetch a code exactly as stored. Callers normalise before calling."""
        result = await self._db.execute(
            select(EstateJoinCode).where(EstateJoinCode.code == code)
        )
        return result.scalar_one_or_none()

    async def get_unrevoked_for_estate(self, estate_id: int) -> EstateJoinCode | None:
        """The one row the "one live code per estate" index cares about.

        An expired-but-unrevoked row still counts: rotation has to revoke it
        before the new code can be inserted.
        """
        result = await self._db.execute(
            select(EstateJoinCode)
            .where(
                EstateJoinCode.estate_id == estate_id,
                EstateJoinCode.revoked_at.is_(None),
            )
            .order_by(EstateJoinCode.code_id.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def get_active_for_estate(
        self, *, estate_id: int, now: datetime
    ) -> EstateJoinCode | None:
        """The code a resident could actually redeem right now, if any."""
        result = await self._db.execute(
            select(EstateJoinCode)
            .where(
                EstateJoinCode.estate_id == estate_id,
                EstateJoinCode.revoked_at.is_(None),
                or_(
                    EstateJoinCode.expires_at.is_(None),
                    EstateJoinCode.expires_at > now,
                ),
            )
            .order_by(EstateJoinCode.code_id.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def add(self, **fields: object) -> EstateJoinCode:
        """Insert one code without committing."""
        row = EstateJoinCode(**fields)
        self._db.add(row)
        await self._db.flush()
        return row

    async def revoke(self, row: EstateJoinCode, *, revoked_at: datetime) -> EstateJoinCode:
        """Mark a code as revoked without committing."""
        row.revoked_at = revoked_at
        self._db.add(row)
        await self._db.flush()
        return row
