"""Investment DTO and dependency wiring; all financial logic is in services."""
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import Page
from app.db.session import get_db
from app.identity.api.dependencies import CurrentUser
from app.property.schemas.investment import (
    InvestmentCalculationRequest, InvestmentInputs, InvestmentResult,
    InvestmentScenarioCreate, InvestmentScenarioResponse,
)
from app.property.services.investment_service import InvestmentService

router = APIRouter(prefix='/investment-scenarios', tags=['investments'])
Database = Annotated[AsyncSession, Depends(get_db)]
EstateId = Annotated[int, Query(gt=0, le=2147483647)]


@router.get('/presets/musgrave', response_model=InvestmentInputs)
async def musgrave_inputs(db: Database, current_user: CurrentUser, estate_id: EstateId, property_id: Annotated[int, Query(gt=0, le=2147483647)]):
    """Fictional assumptions for an authorized existing property; nothing is saved."""
    return await InvestmentService(db).preset(current_user, estate_id=estate_id, property_id=property_id)


@router.post('/calculate', response_model=InvestmentResult)
async def calculate(payload: InvestmentCalculationRequest, db: Database, current_user: CurrentUser):
    return await InvestmentService(db).preview(payload, current_user)


@router.post('', response_model=InvestmentScenarioResponse, status_code=201)
async def save_scenario(payload: InvestmentScenarioCreate, db: Database, current_user: CurrentUser):
    """Create an immutable snapshot; revision_of creates a new linked snapshot."""
    return await InvestmentService(db).save(payload, current_user)


@router.get('', response_model=Page[InvestmentScenarioResponse])
async def list_scenarios(db: Database, current_user: CurrentUser, estate_id: EstateId,
                         page: Annotated[int, Query(ge=1)] = 1, size: Annotated[int, Query(ge=1, le=100)] = 20):
    return await InvestmentService(db).list_mine(current_user, estate_id=estate_id, page=page, size=size)


@router.get('/{scenario_id}', response_model=InvestmentScenarioResponse)
async def get_scenario(scenario_id: Annotated[int, Path(gt=0, le=2147483647)], db: Database, current_user: CurrentUser, estate_id: EstateId):
    return await InvestmentService(db).get(scenario_id, current_user, estate_id=estate_id)
