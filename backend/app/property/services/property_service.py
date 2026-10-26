from decimal import Decimal
import secrets

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
from app.property.repositories.property_photo_repository import PropertyPhotoRepository
from app.property.schemas.property import (
    BulkUnitsRequest,
    PropertyCreate,
    PropertyResponse,
    PropertyUpdate,
)


class PropertyService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repo = PropertyRepository(db)
        self._photo_repo = PropertyPhotoRepository(db)
        self._estate_repo = EstateRepository(db)
        self._estate_authorization = EstateAuthorizationService(db)

    async def update_property(self, unit_id: int, payload: PropertyUpdate, actor: User,
                              *, estate_id: int) -> PropertyResponse:
        await self._estate_authorization.require_role(actor=actor, estate_id=estate_id,
            allowed_roles=('hoa_admin',))
        unit = await self._get_or_404_in_estate(unit_id=unit_id, estate_id=estate_id)
        changes = payload.model_dump(exclude_unset=True)
        # Public identifiers are stable random handles, never internal unit numbers.
        if changes.get("is_public_listing") is True and not unit.public_listing_id:
            unit.public_listing_id = secrets.token_urlsafe(24)[:32]
        if changes.get("is_public_listing") is False:
            unit.public_listing_id = None
        if 'street_address' in changes:
            if not changes['street_address'] or not changes['street_address'].strip():
                raise ConflictException('A street address is required.')
            changes['street_address'] = changes['street_address'].strip()
        for key in ('listing_title', 'listing_description'):
            if key in changes and isinstance(changes[key], str):
                changes[key] = changes[key].strip() or None
        if changes.get('is_public_listing') is True:
            title = changes.get('listing_title', unit.listing_title)
            description = changes.get('listing_description', unit.listing_description)
            amenities = changes.get('amenities', unit.amenities or [])
            if not title or not title.strip() or not description or not description.strip():
                raise ConflictException('Add a listing title and description before publishing this unit.')
            if not amenities:
                raise ConflictException('Add at least one amenity before publishing this unit.')
            bedrooms = changes.get('bedrooms', unit.bedrooms)
            bathrooms = changes.get('bathrooms', unit.bathrooms)
            size_m2 = changes.get('size_m2', unit.size_m2)
            if bedrooms is None or bathrooms is None or size_m2 is None:
                raise ConflictException('Add bedrooms, bathrooms and floor area before publishing this unit.')
            if await self._photo_repo.count_for_property(property_id=unit.unit_id) < 1:
                raise ConflictException('Upload at least one photograph before publishing this unit.')
        for key, value in changes.items():
            setattr(unit, key, value)
        await self._repo.flush()
        await self._db.commit()
        return PropertyResponse.model_validate(unit)

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
            actor=actor, estate_id=estate_id
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
            actor=actor, estate_id=estate_id
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
        fields = payload.model_dump()
        fields['unit_no'] = fields['unit_no'].strip()
        fields['complex_name'] = fields['complex_name'].strip()
        fields['street_address'] = fields['street_address'].strip()
        if fields.get('suburb'):
            fields['suburb'] = fields['suburb'].strip()
        # Complex and suburb are sourced from the authoritative estate record.
        estate = await self._estate_repo.get_by_id(payload.estate_id)
        if estate is None:
            raise NotFoundException(f"Estate with id {payload.estate_id} was not found.")
        fields['complex_name'] = estate.name
        fields['suburb'] = estate.suburb
        property_ = await self._repo.create(**fields)
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
