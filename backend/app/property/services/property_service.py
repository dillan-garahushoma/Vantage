from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.common.enums import UserRole
from app.identity.models.user import User
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.property.models.property import Property
from app.property.repositories.property_repository import PropertyRepository
from app.property.schemas.property import (
    PaginatedPropertiesResponse,
    PropertyCreate,
    PropertyResponse,
)


class PropertyService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = PropertyRepository(db)
        self._estate_authorization = EstateAuthorizationService(db)

    async def search_properties(
        self,
        *,
        page: int,
        page_size: int,
        bedrooms: int | None = None,
        bathrooms: int | None = None,
        min_size_m2: Decimal | None = None,
        max_size_m2: Decimal | None = None,
        estate_id: int,
        actor: User,
    ) -> PaginatedPropertiesResponse:
        await self._estate_authorization.require_membership(
            user_id=actor.user_id, estate_id=estate_id
        )
        offset = (page - 1) * page_size
        properties = await self._repo.search(
            offset=offset,
            limit=page_size,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            min_size_m2=min_size_m2,
            max_size_m2=max_size_m2,
            estate_id=estate_id,
        )
        total = await self._repo.count(
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            min_size_m2=min_size_m2,
            max_size_m2=max_size_m2,
            estate_id=estate_id,
        )
        return PaginatedPropertiesResponse(
            count=total,
            page=page,
            page_size=page_size,
            properties=[PropertyResponse.model_validate(p) for p in properties],
        )

    async def get_property(
        self, *, unit_id: int, estate_id: int, actor: User
    ) -> PropertyResponse:
        await self._estate_authorization.require_membership(
            user_id=actor.user_id, estate_id=estate_id
        )
        property_ = await self._get_or_404_in_estate(unit_id=unit_id, estate_id=estate_id)
        return PropertyResponse.model_validate(property_)

    async def _get_or_404_in_estate(self, *, unit_id: int, estate_id: int) -> Property:
        property_ = await self._repo.get_by_id_in_estate(unit_id=unit_id, estate_id=estate_id)
        if property_ is None:
            raise NotFoundException(f"Property with id {unit_id} was not found.")
        return property_

    async def create_property(self, payload: PropertyCreate, actor: User) -> PropertyResponse:
        await self._estate_authorization.require_role(
            actor=actor,
            estate_id=payload.estate_id,
            allowed_roles=(UserRole.hoa_admin.value,),
        )
        if await self._repo.get_by_unit_no(payload.unit_no) is not None:
            raise ConflictException(f"A property with unit number {payload.unit_no} already exists.")
        property_ = await self._repo.create(**payload.model_dump())
        return PropertyResponse.model_validate(property_)
