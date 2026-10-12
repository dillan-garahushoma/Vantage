from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.common.pagination import Page
from app.common.validators import normalise_email
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.identity.models.user import User
from app.providers.repositories.service_provider_repository import ServiceProviderRepository
from app.providers.schemas.service_provider import (
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
        estate_id: int,
        page: int,
        size: int,
        trade: str | None = None,
        verified: bool | None = None,
        emergency_available: bool | None = None,
    ) -> Page[ServiceProviderResponse]:
        """This estate's provider directory, for an HOA admin of this estate.

        Only providers who hold a service_provider membership of *this* estate are
        returned, and the caller must administer it. Provider phone numbers and
        email addresses are part of the response and are shown **only** here (and
        on ``GET /providers/me`` for the provider themself), never to a resident.
        """
        await self._require_estate_admin(actor, estate_id)
        providers = await self._repo.get_all_in_estate(
            estate_id=estate_id,
            offset=(page - 1) * size,
            limit=size,
            trade=trade, verified=verified, emergency_available=emergency_available
        )
        total = await self._repo.count_in_estate(
            estate_id=estate_id,
            trade=trade, verified=verified, emergency_available=emergency_available
        )
        return Page[ServiceProviderResponse](
            items=[ServiceProviderResponse.model_validate(p) for p in providers],
            total=total,
            page=page,
            size=size,
        )

    async def get_provider(
        self, provider_id: int, actor: User, *, estate_id: int
    ) -> ServiceProviderResponse:
        """One provider of this estate: an HOA admin may read any, a provider only themself."""
        if actor.role == UserRole.hoa_admin.value:
            await self._require_estate_admin(actor, estate_id)
            provider = await self._repo.get_by_id_in_estate(
                provider_id=provider_id, estate_id=estate_id
            )
        elif actor.role == UserRole.service_provider.value:
            await self._require_estate_provider(actor, estate_id)
            provider = await self._repo.get_by_user_id(actor.user_id)
            if provider is not None and provider.provider_id != provider_id:
                raise ForbiddenException("You may only access your own service provider profile.")
        else:
            raise ForbiddenException("You are not permitted to access service provider profiles.")

        if provider is None:
            raise NotFoundException(f"Service provider with id {provider_id} was not found.")
        return ServiceProviderResponse.model_validate(provider)

    async def get_my_provider(self, actor: User) -> ServiceProviderResponse:
        """The signed-in service provider's own profile, wherever they work."""
        if actor.role != UserRole.service_provider.value:
            raise ForbiddenException("Only a service provider has a provider profile.")
        provider = await self._repo.get_by_user_id(actor.user_id)
        if provider is None:
            raise NotFoundException("Your account has no service provider profile.")
        return ServiceProviderResponse.model_validate(provider)

    async def _require_estate_admin(self, actor: User, estate_id: int) -> None:
        """Both credential halves: the global role *and* an admin membership here."""
        await self._estate_authorization.require_role(
            actor=actor,
            estate_id=estate_id,
            allowed_roles=(UserRole.hoa_admin.value,),
        )

    async def _require_estate_provider(self, actor: User, estate_id: int) -> None:
        await self._estate_authorization.require_role(
            actor=actor,
            estate_id=estate_id,
            allowed_roles=(UserRole.service_provider.value,),
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
