from sqlalchemy.ext.asyncio import AsyncSession

from app.common.validators import normalise_email
from app.core.exceptions import ConflictException, NotFoundException
from app.providers.repositories.service_provider_repository import ServiceProviderRepository
from app.providers.schemas.service_provider import (
    PaginatedProvidersResponse,
    ServiceProviderCreate,
    ServiceProviderResponse,
    ServiceProviderUpdate,
)


class ServiceProviderService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = ServiceProviderRepository(db)

    async def list_providers(
        self,
        *,
        trade: str | None = None,
        verified: bool | None = None,
        emergency_available: bool | None = None,
    ) -> PaginatedProvidersResponse:
        providers = await self._repo.get_all(
            trade=trade, verified=verified, emergency_available=emergency_available
        )
        return PaginatedProvidersResponse(
            count=len(providers),
            providers=[ServiceProviderResponse.model_validate(p) for p in providers],
        )

    async def get_provider(self, provider_id: int) -> ServiceProviderResponse:
        provider = await self._repo.get_by_id(provider_id)
        if provider is None:
            raise NotFoundException(f"Service provider with id {provider_id} was not found.")
        return ServiceProviderResponse.model_validate(provider)

    async def create_provider(self, payload: ServiceProviderCreate) -> ServiceProviderResponse:
        email = normalise_email(str(payload.email))
        if await self._repo.get_by_email(email) is not None:
            raise ConflictException("A service provider with this email already exists.")
        provider = await self._repo.create(
            full_name=payload.full_name.strip(),
            trade=payload.trade.strip(),
            phone=payload.phone.strip(),
            email=email,
            verified=payload.verified,
            emergency_available=payload.emergency_available,
        )
        return ServiceProviderResponse.model_validate(provider)

    async def update_provider(
        self, provider_id: int, payload: ServiceProviderUpdate
    ) -> ServiceProviderResponse:
        provider = await self._repo.get_by_id(provider_id)
        if provider is None:
            raise NotFoundException(f"Service provider with id {provider_id} was not found.")

        changes = payload.model_dump(exclude_unset=True)
        # every provider column is NOT NULL (or boolean), so ignore explicit nulls
        changes = {key: value for key, value in changes.items() if value is not None}

        if "email" in changes:
            email = normalise_email(str(changes["email"]))
            existing = await self._repo.get_by_email(email)
            if existing is not None and existing.provider_id != provider.provider_id:
                raise ConflictException("A service provider with this email already exists.")
            changes["email"] = email

        for field, value in changes.items():
            setattr(provider, field, value)
        provider = await self._repo.save(provider)
        return ServiceProviderResponse.model_validate(provider)
