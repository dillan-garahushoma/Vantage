from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.common.validators import normalise_email
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.identity.models.user import User
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
        self._estate_authorization = EstateAuthorizationService(db)

    async def list_providers(
        self,
        *,
        actor: User,
        trade: str | None = None,
        verified: bool | None = None,
        emergency_available: bool | None = None,
    ) -> PaginatedProvidersResponse:
        await self._require_hoa_admin_membership(actor)
        providers = await self._repo.get_all(
            trade=trade, verified=verified, emergency_available=emergency_available
        )
        return PaginatedProvidersResponse(
            count=len(providers),
            providers=[ServiceProviderResponse.model_validate(p) for p in providers],
        )

    async def get_provider(self, provider_id: int, actor: User) -> ServiceProviderResponse:
        if actor.role == UserRole.hoa_admin.value:
            await self._require_hoa_admin_membership(actor)
            provider = await self._repo.get_by_id(provider_id)
        elif actor.role == UserRole.service_provider.value:
            provider = await self._repo.get_by_user_id(actor.user_id)
            if provider is not None and provider.provider_id != provider_id:
                raise ForbiddenException("You may only access your own service provider profile.")
        else:
            raise ForbiddenException("You are not permitted to access service provider profiles.")

        if provider is None:
            raise NotFoundException(f"Service provider with id {provider_id} was not found.")
        return ServiceProviderResponse.model_validate(provider)

    async def _require_hoa_admin_membership(self, actor: User) -> None:
        has_admin_membership = (
            actor.role == UserRole.hoa_admin.value
            and await self._estate_authorization.has_membership_role_in_any_estate(
                user_id=actor.user_id,
                membership_role=UserRole.hoa_admin.value,
            )
        )
        if not has_admin_membership:
            raise ForbiddenException(
                "An HOA administrator membership in at least one estate is required."
            )

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
