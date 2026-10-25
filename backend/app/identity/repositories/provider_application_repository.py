from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.models.provider_application import ProviderApplication


class ProviderApplicationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def has_pending(self, *, estate_id: int, email: str) -> bool:
        result = await self._db.execute(
            select(ProviderApplication.application_id)
            .where(
                ProviderApplication.estate_id == estate_id,
                ProviderApplication.email == email,
                ProviderApplication.status == "pending",
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def add(self, **fields: object) -> ProviderApplication:
        application = ProviderApplication(**fields)
        self._db.add(application)
        await self._db.flush()
        return application

    async def list_for_estate(
        self, *, estate_id: int, status: str | None
    ) -> list[ProviderApplication]:
        stmt = select(ProviderApplication).where(
            ProviderApplication.estate_id == estate_id
        )
        if status is not None:
            stmt = stmt.where(ProviderApplication.status == status)
        result = await self._db.execute(
            stmt.order_by(ProviderApplication.created_at.desc(), ProviderApplication.application_id.desc())
        )
        return list(result.scalars().all())

    async def get_by_id_in_estate(
        self, *, application_id: int, estate_id: int, for_update: bool = False
    ) -> ProviderApplication | None:
        stmt = select(ProviderApplication).where(
            ProviderApplication.application_id == application_id,
            ProviderApplication.estate_id == estate_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def save(self, application: ProviderApplication) -> ProviderApplication:
        await self._db.flush()
        return application
