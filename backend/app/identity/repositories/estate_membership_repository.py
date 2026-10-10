from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.models.estate_membership import EstateMembership


class EstateMembershipRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def has_estate_access(self, *, user_id: int, estate_id: int) -> bool:
        result = await self._db.execute(
            select(EstateMembership.membership_id).where(
                EstateMembership.user_id == user_id,
                EstateMembership.estate_id == estate_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def has_membership_role_for_user(
        self, *, user_id: int, membership_role: str
    ) -> bool:
        result = await self._db.execute(
            select(EstateMembership.membership_id)
            .where(
                EstateMembership.user_id == user_id,
                EstateMembership.membership_role == membership_role,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def list_for_user_and_estate(
        self, *, user_id: int, estate_id: int
    ) -> list[EstateMembership]:
        result = await self._db.execute(
            select(EstateMembership)
            .where(
                EstateMembership.user_id == user_id,
                EstateMembership.estate_id == estate_id,
            )
            .order_by(EstateMembership.membership_id)
        )
        return list(result.scalars().all())

    async def get_for_user_and_estate(
        self, *, user_id: int, estate_id: int
    ) -> EstateMembership | None:
        result = await self._db.execute(
            select(EstateMembership)
            .where(
                EstateMembership.user_id == user_id,
                EstateMembership.estate_id == estate_id,
            )
            .order_by(EstateMembership.membership_id)
            .limit(1)
        )
        return result.scalars().first()

    async def get_for_user_and_property(
        self, *, user_id: int, property_id: int
    ) -> EstateMembership | None:
        result = await self._db.execute(
            select(EstateMembership).where(
                EstateMembership.user_id == user_id,
                EstateMembership.property_id == property_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **fields: object) -> EstateMembership:
        membership = EstateMembership(**fields)
        self._db.add(membership)
        await self._db.commit()
        await self._db.refresh(membership)
        return membership
