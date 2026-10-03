from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.models.service_provider import ServiceProvider


class ServiceProviderRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_all(
        self,
        *,
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
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, provider_id: int) -> ServiceProvider | None:
        result = await self._db.execute(
            select(ServiceProvider).where(ServiceProvider.provider_id == provider_id)
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
