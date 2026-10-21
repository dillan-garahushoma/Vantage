"""Authorize hypothetical investments; persist private versioned snapshots."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import Page
from app.core.exceptions import ForbiddenException, NotFoundException
from app.identity.models.user import User
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.property.repositories.investment_repository import InvestmentRepository
from app.property.repositories.property_repository import PropertyRepository
from app.property.schemas.investment import (
    InvestmentCalculationRequest, InvestmentInputs, InvestmentScenarioCreate, InvestmentScenarioResponse,
)
from app.property.services.investment_calculator import calculate_investment, musgrave_preset


class InvestmentService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._authorization = EstateAuthorizationService(db)
        self._properties = PropertyRepository(db)
        self._repo = InvestmentRepository(db)

    async def _property_access(self, actor: User, estate_id: int, property_id: int):
        access = await self._authorization.resolve_access(actor, estate_id)
        property_ = await self._properties.get_by_id_in_estate(unit_id=property_id, estate_id=estate_id)
        if property_ is None:
            raise NotFoundException('Property was not found in this estate.')
        privileged = access.is_estate_admin or (
            actor.role in {'investor', 'estate_agent'} and actor.role in access.membership_roles
        )
        own_unit = actor.role == 'resident' and 'resident' in access.membership_roles and property_id in access.property_ids
        if not privileged and not own_unit:
            raise ForbiddenException('Your estate membership does not permit modelling this property.')
        return access

    async def preset(self, actor: User, *, estate_id: int, property_id: int) -> InvestmentInputs:
        await self._property_access(actor, estate_id, property_id)
        return InvestmentInputs.model_validate(musgrave_preset())

    async def preview(self, payload: InvestmentCalculationRequest, actor: User):
        await self._property_access(actor, payload.estate_id, payload.property_id)
        return calculate_investment(payload.assumptions)

    async def save(self, payload: InvestmentScenarioCreate, actor: User) -> InvestmentScenarioResponse:
        await self._property_access(actor, payload.estate_id, payload.property_id)
        if payload.revision_of is not None:
            parent = await self._repo.get_owned(scenario_id=payload.revision_of, estate_id=payload.estate_id, owner_id=actor.user_id)
            if parent is None or parent.property_id != payload.property_id:
                raise NotFoundException('Prior investment scenario was not found.')
        result = calculate_investment(payload.assumptions)
        try:
            row = await self._repo.add(
                estate_id=payload.estate_id, property_id=payload.property_id, owner_id=actor.user_id,
                name=payload.name.strip(), revision_of=payload.revision_of, formula_version=result.formula_version,
                assumptions=payload.assumptions.model_dump(mode='json'), result=result.model_dump(mode='json'),
            )
            response = InvestmentScenarioResponse.model_validate(row)
            await self._db.commit()
        except Exception:
            await self._db.rollback()
            raise
        return response

    async def get(self, scenario_id: int, actor: User, *, estate_id: int) -> InvestmentScenarioResponse:
        await self._authorization.resolve_access(actor, estate_id)
        row = await self._repo.get_owned(scenario_id=scenario_id, estate_id=estate_id, owner_id=actor.user_id)
        if row is None:
            raise NotFoundException('Investment scenario was not found.')
        return InvestmentScenarioResponse.model_validate(row)

    async def list_mine(self, actor: User, *, estate_id: int, page: int, size: int) -> Page[InvestmentScenarioResponse]:
        await self._authorization.resolve_access(actor, estate_id)
        rows = await self._repo.list_owned(estate_id=estate_id, owner_id=actor.user_id, offset=(page - 1) * size, limit=size)
        total = await self._repo.count_owned(estate_id=estate_id, owner_id=actor.user_id)
        return Page[InvestmentScenarioResponse](items=[InvestmentScenarioResponse.model_validate(row) for row in rows], total=total, page=page, size=size)
