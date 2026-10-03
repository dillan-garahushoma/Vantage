from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.db.session import get_db
from app.identity.api.dependencies import CurrentUser, require_roles
from app.identity.models.user import User
from app.property.schemas.sale import PaginatedSalesResponse, SaleCreate, SaleResponse
from app.property.services.sale_service import SaleService

router = APIRouter(prefix="/sales", tags=["sales"])


@router.get("", response_model=PaginatedSalesResponse)
async def list_sales(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    unit_id: Annotated[int | None, Query(ge=1)] = None,
) -> PaginatedSalesResponse:
    return await SaleService(db).list_sales(page=page, page_size=page_size, unit_id=unit_id)


@router.get("/{sale_id}", response_model=SaleResponse)
async def get_sale(
    sale_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: CurrentUser,
) -> SaleResponse:
    return await SaleService(db).get_sale(sale_id)


@router.post("", response_model=SaleResponse, status_code=201)
async def create_sale(
    payload: SaleCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _actor: Annotated[
        User, require_roles(UserRole.estate_agent.value, UserRole.hoa_admin.value)
    ],
) -> SaleResponse:
    return await SaleService(db).create_sale(payload)
