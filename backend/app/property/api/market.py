"""DTO validation, authentication and dependency wiring for current marketing."""
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import Page
from app.db.session import get_db
from app.identity.api.dependencies import CurrentUser
from app.property.schemas.market import (
    AuthorityCreate, AuthorityResponse, RequestCreate, RequestDecision, RequestResponse,
    ListingCreate, ListingResponse, ListingAction, ListingContent, PriceChange, PriceResponse,
    CompletionCreate, TransactionResponse, EventResponse, Reason,
)
from app.property.services.market_service import MarketService

router = APIRouter(prefix='/property-market', tags=['property-market'])
Database = Annotated[AsyncSession, Depends(get_db)]
Estate = Annotated[int, Query(gt=0, le=2147483647)]
Key = Annotated[int, Path(gt=0, le=2147483647)]
PageNumber = Annotated[int, Query(ge=1, le=2147483647)]
PageSize = Annotated[int, Query(ge=1, le=100)]


@router.post('/authorities', response_model=AuthorityResponse, status_code=201)
async def create_authority(payload: AuthorityCreate, db: Database, current_user: CurrentUser, estate_id: Estate):
    return await MarketService(db).create_authority(estate_id, payload, current_user)


@router.post('/authorities/{authority_id}/revoke', response_model=AuthorityResponse)
async def revoke_authority(authority_id: Key, payload: Reason, db: Database, current_user: CurrentUser, estate_id: Estate):
    return await MarketService(db).revoke_authority(estate_id, authority_id, payload, current_user)


@router.post('/requests', response_model=RequestResponse, status_code=201)
async def create_request(payload: RequestCreate, db: Database, current_user: CurrentUser, estate_id: Estate):
    return await MarketService(db).create_request(estate_id, payload, current_user)


@router.get('/requests/{request_id}', response_model=RequestResponse)
async def get_request(request_id: Key, db: Database, current_user: CurrentUser, estate_id: Estate):
    return await MarketService(db).get_request(estate_id, request_id, current_user)


@router.post('/requests/{request_id}/decision', response_model=RequestResponse)
async def decide_request(request_id: Key, payload: RequestDecision, db: Database, current_user: CurrentUser, estate_id: Estate):
    return await MarketService(db).decide_request(estate_id, request_id, payload, current_user)


@router.post('/requests/{request_id}/cancel', response_model=RequestResponse)
async def cancel_request(request_id: Key, payload: Reason, db: Database, current_user: CurrentUser, estate_id: Estate):
    return await MarketService(db).cancel_request(estate_id, request_id, payload, current_user)


@router.get('/requests/{request_id}/history', response_model=Page[EventResponse])
async def request_history(request_id: Key, db: Database, current_user: CurrentUser, estate_id: Estate,
                          page: PageNumber = 1, size: PageSize = 20):
    return await MarketService(db).collection(estate_id, 'request_events', current_user,
                                              page=page, size=size, entity_id=request_id)


@router.post('/listings', response_model=ListingResponse, status_code=201)
async def create_listing(payload: ListingCreate, db: Database, current_user: CurrentUser, estate_id: Estate):
    return await MarketService(db).create_listing(estate_id, payload, current_user)


@router.get('/listings/{listing_id}', response_model=ListingResponse)
async def get_listing(listing_id: Key, db: Database, current_user: CurrentUser, estate_id: Estate):
    return await MarketService(db).get_listing(estate_id, listing_id, current_user)


@router.post('/listings/{listing_id}/actions', response_model=ListingResponse)
async def listing_action(listing_id: Key, payload: ListingAction, db: Database, current_user: CurrentUser, estate_id: Estate):
    return await MarketService(db).listing_action(estate_id, listing_id, payload, current_user)


@router.patch('/listings/{listing_id}', response_model=ListingResponse)
async def edit_listing_content(listing_id: Key, payload: ListingContent, db: Database, current_user: CurrentUser, estate_id: Estate):
    return await MarketService(db).edit_content(estate_id, listing_id, payload, current_user)


@router.patch('/listings/{listing_id}/price', response_model=ListingResponse)
async def listing_price(listing_id: Key, payload: PriceChange, db: Database, current_user: CurrentUser, estate_id: Estate):
    return await MarketService(db).change_price(estate_id, listing_id, payload, current_user)


@router.get('/listings/{listing_id}/price-history', response_model=Page[PriceResponse])
async def price_history(listing_id: Key, db: Database, current_user: CurrentUser, estate_id: Estate,
                        page: PageNumber = 1, size: PageSize = 20):
    return await MarketService(db).collection(estate_id, 'prices', current_user,
                                              page=page, size=size, entity_id=listing_id)


@router.get('/listings/{listing_id}/history', response_model=Page[EventResponse])
async def listing_history(listing_id: Key, db: Database, current_user: CurrentUser, estate_id: Estate,
                          page: PageNumber = 1, size: PageSize = 20):
    return await MarketService(db).collection(estate_id, 'listing_events', current_user,
                                              page=page, size=size, entity_id=listing_id)


@router.post('/listings/{listing_id}/complete', response_model=TransactionResponse, status_code=201)
async def complete_listing(listing_id: Key, payload: CompletionCreate, db: Database, current_user: CurrentUser, estate_id: Estate):
    return await MarketService(db).complete(estate_id, listing_id, payload, current_user)


def _collection_endpoint(kind):
    async def endpoint(db: Database, current_user: CurrentUser, estate_id: Estate,
                       page: PageNumber = 1, size: PageSize = 20):
        return await MarketService(db).collection(estate_id, kind, current_user, page=page, size=size)
    return endpoint


for _kind, _dto in (('authorities', AuthorityResponse), ('requests', RequestResponse),
                    ('listings', ListingResponse), ('sales', TransactionResponse), ('rentals', TransactionResponse)):
    router.add_api_route('/' + _kind, _collection_endpoint(_kind), methods=['GET'],
                         response_model=Page[_dto], name='list_market_' + _kind)
