from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.identity.models.estate_membership import EstateMembership
from app.identity.models.user import User
from app.providers.models.service_provider import ServiceProvider


def _estate_member_statement(*, estate_id: int):
    """Providers whose linked account holds a service_provider membership here.

    The estate is the tenant boundary, so "the provider directory" means the
    providers who actually work in *this* estate - not every provider row in the
    database. ``distinct`` collapses a provider whose account holds more than one
    membership row in the same estate; a legacy provider row with
    ``user_id IS NULL`` can never be a member and is excluded by the join.
    """
    return (
        select(ServiceProvider)
        .join(EstateMembership, EstateMembership.user_id == ServiceProvider.user_id)
        .join(User, User.user_id == ServiceProvider.user_id)
        .where(
            EstateMembership.estate_id == estate_id,
            EstateMembership.membership_role == UserRole.service_provider.value,
            User.role == UserRole.service_provider.value,
        )
        .distinct()
    )


class ServiceProviderRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_all(
        self,
        *,
        offset: int,
        limit: int,
        trade: str | None = None,
        verified: bool | None = None,
        emergency_available: bool | None = None,
    ) -> list[ServiceProvider]:
        stmt = select(ServiceProvider).order_by(ServiceProvider.provider_id)
        if trade is not None:
            stmt = stmt.where(ServiceProvider.trade.ilike(trade))
        if verified is not None:
            stmt = stmt.where(ServiceProvider.verified == verified)
        if emergency_available is not None:
            stmt = stmt.where(ServiceProvider.emergency_available == emergency_available)
        result = await self._db.execute(stmt.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count_all(
        self,
        *,
        trade: str | None = None,
        verified: bool | None = None,
        emergency_available: bool | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(ServiceProvider)
        if trade is not None:
            stmt = stmt.where(ServiceProvider.trade.ilike(trade))
        if verified is not None:
            stmt = stmt.where(ServiceProvider.verified == verified)
        if emergency_available is not None:
            stmt = stmt.where(ServiceProvider.emergency_available == emergency_available)
        result = await self._db.execute(stmt)
        return int(result.scalar_one())

    async def get_by_id(self, provider_id: int) -> ServiceProvider | None:
        result = await self._db.execute(
            select(ServiceProvider).where(ServiceProvider.provider_id == provider_id)
        )
        return result.scalar_one_or_none()

    async def get_all_in_estate(
        self,
        *,
        estate_id: int,
        offset: int,
        limit: int,
        trade: str | None = None,
        verified: bool | None = None,
        emergency_available: bool | None = None,
    ) -> list[ServiceProvider]:
        """One page of the providers who are members of this estate."""
        stmt = _estate_member_statement(estate_id=estate_id)
        if trade is not None:
            stmt = stmt.where(ServiceProvider.trade.ilike(trade))
        if verified is not None:
            stmt = stmt.where(ServiceProvider.verified == verified)
        if emergency_available is not None:
            stmt = stmt.where(ServiceProvider.emergency_available == emergency_available)
        stmt = stmt.order_by(ServiceProvider.provider_id)
        result = await self._db.execute(stmt.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count_in_estate(
        self,
        *,
        estate_id: int,
        trade: str | None = None,
        verified: bool | None = None,
        emergency_available: bool | None = None,
    ) -> int:
        """How many member providers this estate has, honouring the same filters."""
        provider_ids = _estate_member_statement(estate_id=estate_id).with_only_columns(
            ServiceProvider.provider_id
        )
        if trade is not None:
            provider_ids = provider_ids.where(ServiceProvider.trade.ilike(trade))
        if verified is not None:
            provider_ids = provider_ids.where(ServiceProvider.verified == verified)
        if emergency_available is not None:
            provider_ids = provider_ids.where(
                ServiceProvider.emergency_available == emergency_available
            )
        stmt = select(func.count()).select_from(provider_ids.subquery())
        result = await self._db.execute(stmt)
        return int(result.scalar_one())

    async def get_by_id_in_estate(
        self, *, provider_id: int, estate_id: int
    ) -> ServiceProvider | None:
        """Fetch a provider only when they are a member of this estate.

        A provider from another estate is a 404, never a 403 that would confirm
        the row exists.
        """
        stmt = _estate_member_statement(estate_id=estate_id).where(
            ServiceProvider.provider_id == provider_id
        )
        result = await self._db.execute(stmt)
        return result.scalars().first()

    async def get_by_user_id(self, user_id: int) -> ServiceProvider | None:
        result = await self._db.execute(
            select(ServiceProvider).where(ServiceProvider.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> ServiceProvider | None:
        result = await self._db.execute(
            select(ServiceProvider).where(ServiceProvider.email == email)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        full_name: str,
        trade: str,
        phone: str,
        email: str,
        verified: bool,
        emergency_available: bool,
    ) -> ServiceProvider:
        provider = ServiceProvider(
            full_name=full_name,
            trade=trade,
            phone=phone,
            email=email,
            verified=verified,
            emergency_available=emergency_available,
            total_reviews=0,
        )
        self._db.add(provider)
        await self._db.commit()
        await self._db.refresh(provider)
        return provider

    async def save(self, provider: ServiceProvider) -> ServiceProvider:
        await self._db.commit()
        await self._db.refresh(provider)
        return provider

    async def add(
        self,
        *,
        full_name: str,
        trade: str,
        phone: str,
        email: str,
        verified: bool = False,
        emergency_available: bool = False,
        user_id: int | None = None,
    ) -> ServiceProvider:
        """Add a provider profile without committing; the signup service commits once."""
        provider = ServiceProvider(
            user_id=user_id,
            full_name=full_name,
            trade=trade,
            phone=phone,
            email=email,
            verified=verified,
            emergency_available=emergency_available,
            total_reviews=0,
        )
        self._db.add(provider)
        await self._db.flush()
        return provider
