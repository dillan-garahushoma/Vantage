"""Current estate marketing use cases. One commit per multi-step write.

All writers lock the estate-scoped unit first, then refresh the workflow rows.
This serializes authority revocation, request decisions, pricing and completion
for one unit without relying on browser versions as authorization.
"""
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import Page
from app.core.exceptions import BadRequestException, ConflictException, ForbiddenException, NotFoundException
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.property.models.market import (MarketingAuthority, MarketingRequest, MarketListing,
                                       ListingPriceEvent, MarketTransaction, MarketEvent)
from app.property.repositories.market_repository import MarketRepository
from app.property.schemas.market import (AuthorityResponse, RequestResponse, ListingResponse,
                                         PriceResponse, TransactionResponse, EventResponse)


class MarketService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._auth = EstateAuthorizationService(db)
        self._repo = MarketRepository(db)

    async def _access(self, actor, estate_id, *, admin=False):
        access = await self._auth.resolve_access(actor, estate_id)
        if admin and not access.is_estate_admin:
            raise ForbiddenException('Estate HOA capability is required.')
        return access

    @staticmethod
    def _agent(actor, access):
        return actor.role == 'estate_agent' and 'estate_agent' in access.membership_roles

    def _participant(self, actor, access, request):
        return access.is_estate_admin or request.requester_id == actor.user_id or (
            self._agent(actor, access) and request.agent_id == actor.user_id)

    def _manager(self, actor, access, request):
        if not (access.is_estate_admin or (self._agent(actor, access) and request.agent_id == actor.user_id)):
            raise ForbiddenException('Only the assigned estate agent or estate HOA may manage this listing.')

    async def _get(self, model, estate_id, key, *, refresh=False):
        row = await self._repo.get(model, estate_id, key, refresh=refresh)
        if row is None:
            raise NotFoundException('Record was not found in this estate.')
        return row

    async def _unit(self, estate_id, property_id):
        row = await self._repo.lock_property(estate_id, property_id)
        if row is None:
            raise NotFoundException('Property was not found in this estate.')
        return row

    async def _event(self, estate_id, kind, key, action, actor, **details):
        await self._repo.add(MarketEvent, estate_id=estate_id, entity_type=kind,
            entity_id=key, action=action, actor_id=actor.user_id, details=details)

    async def _finish(self, row, dto):
        await self._repo.flush()
        result = dto.model_validate(row)
        await self._db.commit()
        return result

    async def _request(self, actor, access, estate_id, request_id, *, write=False):
        row = await self._get(MarketingRequest, estate_id, request_id)
        if not self._participant(actor, access, row):
            raise NotFoundException('Request was not found.')
        if write:
            await self._unit(estate_id, row.property_id)
            row = await self._get(MarketingRequest, estate_id, request_id, refresh=True)
        return row

    async def _listing(self, actor, access, estate_id, listing_id, *, private=False, write=False):
        row = await self._get(MarketListing, estate_id, listing_id)
        request = await self._get(MarketingRequest, estate_id, row.request_id)
        if (private or row.status != 'active') and not self._participant(actor, access, request):
            raise NotFoundException('Listing was not found.')
        if write:
            await self._unit(estate_id, row.property_id)
            row = await self._get(MarketListing, estate_id, listing_id, refresh=True)
            request = await self._get(MarketingRequest, estate_id, row.request_id, refresh=True)
        return row, request

    async def _mandate(self, estate_id, request):
        authority = await self._repo.active_authority(estate_id, request.property_id)
        if (authority is None or authority.authority_id != request.authority_id
                or authority.representative_id != request.requester_id):
            raise ConflictException('The verified marketing authority is no longer current.')
        if await self._repo.member_user(estate_id, request.requester_id) is None:
            raise ConflictException('The marketing representative is no longer an estate member.')

    @staticmethod
    def _editable(listing, expected_version):
        if listing.version != expected_version:
            raise ConflictException('Listing changed. Reload its current version before editing.')
        if listing.status not in {'draft', 'active'}:
            raise ConflictException('This listing is no longer editable.')

    async def create_authority(self, estate_id, payload, actor):
        await self._access(actor, estate_id, admin=True)
        await self._unit(estate_id, payload.property_id)
        if await self._repo.member_user(estate_id, payload.representative_id) is None:
            raise NotFoundException('Representative was not found in this estate.')
        if await self._repo.active_authority(estate_id, payload.property_id):
            raise ConflictException('This unit already has a current marketing representative.')
        row = await self._repo.add(MarketingAuthority, estate_id=estate_id, verified_by=actor.user_id,
                                   **payload.model_dump())
        await self._event(estate_id, 'authority', row.authority_id, 'verified', actor,
                          property_id=row.property_id, representative_id=row.representative_id)
        return await self._finish(row, AuthorityResponse)

    async def revoke_authority(self, estate_id, authority_id, payload, actor):
        await self._access(actor, estate_id, admin=True)
        row = await self._get(MarketingAuthority, estate_id, authority_id)
        await self._unit(estate_id, row.property_id)
        row = await self._get(MarketingAuthority, estate_id, authority_id, refresh=True)
        if row.revoked_at:
            raise ConflictException('Marketing authority is already revoked.')
        row.revoked_at = datetime.now(timezone.utc)
        row.revoked_by = actor.user_id
        request = await self._repo.open_request(estate_id, row.property_id)
        if request:
            request.status = 'cancelled'
            await self._event(estate_id, 'request', request.request_id, 'cancelled', actor, reason=payload.reason)
            listing = await self._repo.listing_for_request(estate_id, request.request_id)
            if listing and listing.status in {'draft', 'active'}:
                listing.status = 'withdrawn'
                listing.version += 1
                await self._event(estate_id, 'listing', listing.listing_id, 'withdrawn', actor, reason=payload.reason)
        await self._event(estate_id, 'authority', authority_id, 'revoked', actor, reason=payload.reason)
        return await self._finish(row, AuthorityResponse)

    async def create_request(self, estate_id, payload, actor):
        await self._access(actor, estate_id)
        await self._unit(estate_id, payload.property_id)
        authority = await self._repo.active_authority(estate_id, payload.property_id)
        if authority is None or authority.representative_id != actor.user_id:
            raise ForbiddenException('An HOA-verified unit marketing authority is required; residency alone is insufficient.')
        if await self._repo.open_request(estate_id, payload.property_id):
            raise ConflictException('An open marketing request already exists for this unit.')
        row = await self._repo.add(MarketingRequest, estate_id=estate_id, authority_id=authority.authority_id,
            requester_id=actor.user_id, status='pending', **payload.model_dump())
        await self._event(estate_id, 'request', row.request_id, 'submitted', actor, purpose=row.purpose)
        return await self._finish(row, RequestResponse)

    async def decide_request(self, estate_id, request_id, payload, actor):
        access = await self._access(actor, estate_id, admin=True)
        row = await self._request(actor, access, estate_id, request_id, write=True)
        if row.status != 'pending':
            raise ConflictException('Only a pending request can be decided.')
        await self._mandate(estate_id, row)
        if payload.decision == 'approved':
            if payload.agent_id is None:
                raise BadRequestException('Approval requires an estate-authorized agent.')
            agent = await self._repo.member_user(estate_id, payload.agent_id)
            if agent is None:
                raise ForbiddenException('Assigned agent must belong to this estate.')
            agent_access = await self._auth.resolve_access(agent, estate_id)
            if not self._agent(agent, agent_access):
                raise ForbiddenException('Assigned agent needs both global and estate agent capability.')
            row.agent_id = agent.user_id
        elif payload.agent_id is not None:
            raise BadRequestException('A rejected request cannot assign an agent.')
        row.status, row.decision_reason = payload.decision, payload.reason
        row.decided_at, row.decided_by = datetime.now(timezone.utc), actor.user_id
        await self._event(estate_id, 'request', request_id, payload.decision, actor,
                          reason=payload.reason, agent_id=row.agent_id)
        return await self._finish(row, RequestResponse)

    async def cancel_request(self, estate_id, request_id, payload, actor):
        access = await self._access(actor, estate_id)
        row = await self._request(actor, access, estate_id, request_id, write=True)
        if not (access.is_estate_admin or row.requester_id == actor.user_id):
            raise ForbiddenException('Only the requester or estate HOA can cancel a request.')
        if row.status not in {'pending', 'approved'}:
            raise ConflictException('Only pending/approved requests can be cancelled; withdraw an existing listing instead.')
        row.status = 'cancelled'
        await self._event(estate_id, 'request', request_id, 'cancelled', actor, reason=payload.reason)
        return await self._finish(row, RequestResponse)

    async def create_listing(self, estate_id, payload, actor):
        access = await self._access(actor, estate_id)
        request = await self._request(actor, access, estate_id, payload.request_id, write=True)
        self._manager(actor, access, request)
        if request.status != 'approved' or await self._repo.listing_for_request(estate_id, request.request_id):
            raise ConflictException('A new listing requires an approved, unlisted request.')
        await self._mandate(estate_id, request)
        row = await self._repo.add(MarketListing, estate_id=estate_id, property_id=request.property_id,
            purpose=request.purpose, status='draft', version=1, **payload.model_dump())
        request.status = 'listed'
        await self._repo.add(ListingPriceEvent, estate_id=estate_id, listing_id=row.listing_id,
            old_price=None, new_price=row.asking_price, changed_by=actor.user_id,
            reason='Initial asking price', listing_version=1)
        await self._event(estate_id, 'listing', row.listing_id, 'created', actor, request_id=request.request_id)
        await self._event(estate_id, 'request', request.request_id, 'listed', actor, listing_id=row.listing_id)
        return await self._finish(row, ListingResponse)

    async def listing_action(self, estate_id, listing_id, payload, actor):
        access = await self._access(actor, estate_id)
        row, request = await self._listing(actor, access, estate_id, listing_id, private=True, write=True)
        # A verified representative can withdraw their own listing, but cannot
        # publish or change the marketing price without the assigned agent/HOA.
        if not (payload.action == 'withdraw' and request.requester_id == actor.user_id):
            self._manager(actor, access, request)
        self._editable(row, payload.expected_version)
        if payload.action == 'publish':
            if row.status != 'draft':
                raise ConflictException('Only a draft listing can be published.')
            await self._mandate(estate_id, request)
            row.status, row.published_at = 'active', datetime.now(timezone.utc)
        else:
            row.status, request.status = 'withdrawn', 'cancelled'
            await self._event(estate_id, 'request', request.request_id, 'cancelled', actor, reason=payload.reason)
        row.version += 1
        await self._event(estate_id, 'listing', listing_id, payload.action, actor, reason=payload.reason)
        return await self._finish(row, ListingResponse)

    async def change_price(self, estate_id, listing_id, payload, actor):
        access = await self._access(actor, estate_id)
        row, request = await self._listing(actor, access, estate_id, listing_id, private=True, write=True)
        self._manager(actor, access, request)
        self._editable(row, payload.expected_version)
        await self._mandate(estate_id, request)
        if row.asking_price == payload.asking_price:
            raise BadRequestException('The new asking price must differ from the current price.')
        old = row.asking_price
        row.asking_price, row.version = payload.asking_price, row.version + 1
        await self._repo.add(ListingPriceEvent, estate_id=estate_id, listing_id=listing_id,
            old_price=old, new_price=row.asking_price, changed_by=actor.user_id,
            reason=payload.reason, listing_version=row.version)
        await self._event(estate_id, 'listing', listing_id, 'price_changed', actor,
                          old_price=str(old), new_price=str(row.asking_price), reason=payload.reason)
        return await self._finish(row, ListingResponse)

    async def edit_content(self, estate_id, listing_id, payload, actor):
        access = await self._access(actor, estate_id)
        row, request = await self._listing(actor, access, estate_id, listing_id, private=True, write=True)
        self._manager(actor, access, request)
        self._editable(row, payload.expected_version)
        await self._mandate(estate_id, request)
        row.title, row.description, row.version = payload.title, payload.description, row.version + 1
        await self._event(estate_id, 'listing', listing_id, 'content_changed', actor,
                          title=payload.title, description=payload.description, reason=payload.reason)
        return await self._finish(row, ListingResponse)

    async def complete(self, estate_id, listing_id, payload, actor):
        access = await self._access(actor, estate_id, admin=True)
        row, request = await self._listing(actor, access, estate_id, listing_id, private=True, write=True)
        self._editable(row, payload.expected_version)
        if row.status != 'active':
            raise ConflictException('Only a published active listing can be completed.')
        await self._mandate(estate_id, request)
        if payload.effective_date > date.today():
            raise BadRequestException('An actual completion date cannot be in the future.')
        transaction = await self._repo.add(MarketTransaction, estate_id=estate_id, property_id=row.property_id,
            listing_id=listing_id, purpose=row.purpose, actual_amount=payload.actual_amount,
            asking_price_at_completion=row.asking_price, effective_date=payload.effective_date,
            recorded_by=actor.user_id, reference=payload.reference)
        row.status, row.version = ('sold' if row.purpose == 'sale' else 'let'), row.version + 1
        request.status = 'fulfilled'
        if row.purpose == 'sale':
            # Completing a recorded sale retires this seller's marketing mandate.
            # A subsequent representative must be independently verified by HOA;
            # this is not an automatic title/estate-membership transfer.
            authority = await self._get(MarketingAuthority, estate_id, request.authority_id)
            authority.revoked_at, authority.revoked_by = datetime.now(timezone.utc), actor.user_id
            await self._event(estate_id, 'authority', authority.authority_id, 'sale_completed', actor,
                              transaction_id=transaction.transaction_id)
        await self._event(estate_id, 'listing', listing_id, 'completed', actor, transaction_id=transaction.transaction_id)
        await self._event(estate_id, 'request', request.request_id, 'fulfilled', actor, transaction_id=transaction.transaction_id)
        return await self._finish(transaction, TransactionResponse)

    async def get_request(self, estate_id, request_id, actor):
        access = await self._access(actor, estate_id)
        return RequestResponse.model_validate(await self._request(actor, access, estate_id, request_id))

    async def get_listing(self, estate_id, listing_id, actor):
        access = await self._access(actor, estate_id)
        row, _ = await self._listing(actor, access, estate_id, listing_id)
        return ListingResponse.model_validate(row)

    async def collection(self, estate_id, kind, actor, *, page=1, size=20, entity_id=None):
        access = await self._access(actor, estate_id)
        mapping = {'authorities': (MarketingAuthority, AuthorityResponse),
                   'requests': (MarketingRequest, RequestResponse), 'listings': (MarketListing, ListingResponse),
                   'sales': (MarketTransaction, TransactionResponse), 'rentals': (MarketTransaction, TransactionResponse),
                   'prices': (ListingPriceEvent, PriceResponse),
                   'listing_events': (MarketEvent, EventResponse), 'request_events': (MarketEvent, EventResponse)}
        model, dto = mapping[kind]
        if kind in {'prices', 'listing_events'}:
            await self._listing(actor, access, estate_id, entity_id, private=True)
        if kind == 'request_events':
            await self._request(actor, access, estate_id, entity_id)
        rows, total = await self._repo.collection(model, estate_id, actor_id=actor.user_id,
            is_admin=access.is_estate_admin, is_agent=self._agent(actor, access),
            offset=(page - 1) * size, limit=size, entity_id=entity_id,
            entity_type='listing' if kind == 'listing_events' else 'request',
            purpose='sale' if kind == 'sales' else 'rent' if kind == 'rentals' else None)
        return Page[dto](items=[dto.model_validate(row) for row in rows], total=total, page=page, size=size)
