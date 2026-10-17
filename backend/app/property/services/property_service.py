from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import Page
from app.core.exceptions import ConflictException, NotFoundException
from app.common.enums import UserRole
from app.identity.models.user import User
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.property.models.property import Property
from app.property.repositories.estate_repository import EstateRepository
from app.property.repositories.property_repository import PropertyRepository
from app.property.schemas.property import (
    BulkUnitsRequest,
    PropertyCreate,
    PropertyResponse,
)


class PropertyService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repo = PropertyRepository(db)
        self._estate_repo = EstateRepository(db)
        self._estate_authorization = EstateAuthorizationService(db)

    async def search_properties(
        self,
        *,
        page: int,
        size: int,
        bedrooms: int | None = None,
        bathrooms: int | None = None,
        min_size_m2: Decimal | None = None,
        max_size_m2: Decimal | None = None,
        estate_id: int,
        actor: User,
    ) -> Page[PropertyResponse]:
        await self._estate_authorization.require_membership(
            user_id=actor.user_id, estate_id=estate_id
        )
        offset = (page - 1) * size
        properties = await self._repo.search(
            offset=offset,
            limit=size,
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
        return Page[PropertyResponse](
            items=[PropertyResponse.model_validate(p) for p in properties],
            total=total,
            page=page,
            size=size,
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
        if await self._repo.get_by_unit_no_in_estate(estate_id=payload.estate_id, unit_no=payload.unit_no) is not None:
            raise ConflictException(f"A property with unit number {payload.unit_no} already exists in this estate.")
        property_ = await self._repo.create(**payload.model_dump())
        return PropertyResponse.model_validate(property_)

    async def create_units_bulk(
        self, payload: BulkUnitsRequest, *, estate_id: int, actor: User
    ) -> list[PropertyResponse]:
        """Create up to 500 units in one estate, all or nothing.

        Both halves of the credential are required: the global ``hoa_admin`` role
        and an ``hoa_admin`` membership of this estate. ``complex_name`` and
        ``suburb`` are copied from the estate itself, so a caller cannot label
        units with a complex they do not administer. Duplicate unit numbers -
        within the request or against what the estate already has - reject the
        whole batch with the offending numbers, and nothing is inserted.
        """
        await self._estate_authorization.require_role(
            actor=actor,
            estate_id=estate_id,
            allowed_roles=(UserRole.hoa_admin.value,),
        )
        estate = await self._estate_repo.get_by_id(estate_id)
        if estate is None:
            raise NotFoundException(f"Estate with id {estate_id} was not found.")

        unit_nos = [item.unit_no.strip() for item in payload.units]
        seen: set[str] = set()
        repeated: set[str] = set()
        for unit_no in unit_nos:
            if unit_no in seen:
                repeated.add(unit_no)
            seen.add(unit_no)

        existing = await self._repo.list_unit_nos_in_estate(estate_id=estate_id)
        clashes = sorted(repeated | {unit_no for unit_no in unit_nos if unit_no in existing})
        if clashes:
            raise ConflictException(
                "These unit numbers already exist in this estate: "
                + ", ".join(clashes)
                + "."
            )

        created: list[Property] = []
        try:
            for item, unit_no in zip(payload.units, unit_nos):
                created.append(
                    await self._repo.add(
                        estate_id=estate_id,
                        unit_no=unit_no,
                        complex_name=estate.name,
                        street_address=item.street_address.strip(),
                        suburb=estate.suburb,
                        size_m2=item.size_m2,
                        bedrooms=item.bedrooms,
                        bathrooms=item.bathrooms,
                    )
                )
            # One commit for the whole batch: a concurrent insert that beat the
            # pre-check rolls the entire batch back rather than half-inserting it.
            await self._db.commit()
        except IntegrityError:
            await self._db.rollback()
            raise ConflictException(
                "One or more of those unit numbers already exist in this estate."
            )
        return [PropertyResponse.model_validate(property_) for property_ in created]
