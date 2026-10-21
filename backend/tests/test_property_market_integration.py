"""Real PostgreSQL/HTTP acceptance. This file never uses mock market storage."""
import asyncio
from datetime import date, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.identity.api.dependencies import get_current_user
from app.identity.models.estate_membership import EstateMembership
from app.main import app
from app.core.exceptions import ConflictException
from app.property.models.market import MarketEvent
from app.property.schemas.market import PriceChange
from app.property.services.market_service import MarketService
from tests.factories import build_two_estate_world

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
BASE = '/api/v1/property-market'


@pytest_asyncio.fixture
async def market(db_session, async_client):
    w = await build_two_estate_world(db_session)
    # Reuse an existing provisioned user as a synthetic estate agent; production
    # registration is not changed by this feature.
    w.provider_user_a.role = 'estate_agent'
    membership = (await db_session.execute(select(EstateMembership).where(
        EstateMembership.user_id == w.provider_user_a.user_id,
        EstateMembership.estate_id == w.estate_a.estate_id))).scalars().first()
    membership.membership_role = 'estate_agent'
    await db_session.commit()

    async def call(actor, method, path, body=None, estate_id=None, **params):
        if actor is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = lambda: actor
        return await async_client.request(method, BASE + path, json=body,
            params={'estate_id': estate_id or w.estate_a.estate_id} | params)

    yield w, call
    app.dependency_overrides.pop(get_current_user, None)


async def authorize_and_request(w, call, purpose='sale'):
    authority = await call(w.hoa_admin_a, 'POST', '/authorities', {
        'property_id': w.property_a1.unit_id, 'representative_id': w.resident_a1.user_id,
        'verification_reference': 'Fictional owner mandate reviewed for test'})
    assert authority.status_code == 201, authority.text
    result = await call(w.resident_a1, 'POST', '/requests', {
        'property_id': w.property_a1.unit_id, 'purpose': purpose,
        'requested_price': '1350000.00' if purpose == 'sale' else '11500.00', 'notes': 'PRIVATE owner request'})
    assert result.status_code == 201, result.text
    return authority.json(), result.json()


async def approved_listing(w, call, purpose='sale'):
    authority, request = await authorize_and_request(w, call, purpose)
    approved = await call(w.hoa_admin_a, 'POST', f"/requests/{request['request_id']}/decision", {
        'decision': 'approved', 'agent_id': w.provider_user_a.user_id, 'reason': 'Owner authority and consent reviewed'})
    assert approved.status_code == 200, approved.text
    listing = await call(w.provider_user_a, 'POST', '/listings', {
        'request_id': request['request_id'], 'title': 'Fictional Musgrave apartment',
        'description': 'A fictional two-bedroom unit used for acceptance tests.',
        'asking_price': request['requested_price']})
    assert listing.status_code == 201, listing.text
    return authority, request, listing.json()


@pytest.mark.parametrize('purpose', ['sale', 'rent'])
async def test_full_request_listing_price_and_completion_flow(market, purpose):
    w, call = market
    _, request, listing = await approved_listing(w, call, purpose)
    ident = listing['listing_id']
    assert listing['status'] == 'draft'
    assert (await call(w.resident_a2, 'GET', f'/listings/{ident}')).status_code == 404
    published = await call(w.provider_user_a, 'POST', f'/listings/{ident}/actions', {
        'action': 'publish', 'expected_version': 1, 'reason': 'Approved description checked'})
    assert published.status_code == 200, published.text
    assert published.json()['status'] == 'active'
    public_read = await call(w.resident_a2, 'GET', f'/listings/{ident}')
    assert public_read.status_code == 200
    assert 'PRIVATE owner request' not in public_read.text
    assert 'verification_reference' not in public_read.json()
    new_price = '1400000.00' if purpose == 'sale' else '12000.00'
    revised = await call(w.provider_user_a, 'PATCH', f'/listings/{ident}/price', {
        'asking_price': new_price, 'expected_version': 2, 'reason': 'Revised owner-approved asking price'})
    assert revised.status_code == 200, revised.text
    assert revised.json()['version'] == 3
    history = await call(w.resident_a1, 'GET', f'/listings/{ident}/price-history')
    assert history.json()['total'] == 2
    assert history.json()['items'][0]['new_price'] == new_price
    assert (await call(w.resident_a2, 'GET', f'/listings/{ident}/price-history')).status_code == 404
    assert (await call(w.provider_user_a, 'PATCH', f'/listings/{ident}/price', {
        'asking_price': '1', 'expected_version': 2, 'reason': 'Stale browser'})).status_code == 409
    actual = '1380000.00' if purpose == 'sale' else '11800.00'
    completed = await call(w.hoa_admin_a, 'POST', f'/listings/{ident}/complete', {
        'actual_amount': actual, 'effective_date': date.today().isoformat(),
        'expected_version': 3, 'reference': 'Fictional completion confirmation'})
    assert completed.status_code == 201, completed.text
    assert completed.json()['actual_amount'] == actual
    assert completed.json()['asking_price_at_completion'] == new_price
    final = (await call(w.resident_a1, 'GET', f'/listings/{ident}')).json()
    assert final['status'] == ('sold' if purpose == 'sale' else 'let')
    assert (await call(w.resident_a1, 'GET', f"/requests/{request['request_id']}")).json()['status'] == 'fulfilled'
    assert (await call(w.hoa_admin_a, 'GET', '/sales')).json()['total'] == (1 if purpose == 'sale' else 0)
    assert (await call(w.resident_a2, 'GET', '/sales')).json()['total'] == 0
    events = (await call(w.resident_a1, 'GET', f'/listings/{ident}/history')).json()
    assert events['total'] == 4
    if purpose == 'sale':
        # A completed sale must not let the previous seller start marketing the
        # property again with the old mandate.
        again = await call(w.resident_a1, 'POST', '/requests', {
            'property_id': w.property_a1.unit_id, 'purpose': 'sale', 'requested_price': '1500000'})
        assert again.status_code == 403


async def test_resident_is_not_owner_and_estate_capability_is_required(market):
    w, call = market
    body = {'property_id': w.property_a1.unit_id, 'purpose': 'sale', 'requested_price': '1350000'}
    assert (await call(w.resident_a1, 'POST', '/requests', body)).status_code == 403
    grant = {'property_id': w.property_a1.unit_id, 'representative_id': w.resident_a1.user_id,
             'verification_reference': 'Test reference'}
    assert (await call(w.resident_a1, 'POST', '/authorities', grant)).status_code == 403
    # Global HOA, but only resident in B: cannot verify ownership in B.
    foreign = grant | {'property_id': w.property_b1.unit_id, 'representative_id': w.resident_b1.user_id}
    assert (await call(w.cross_user, 'POST', '/authorities', foreign, estate_id=w.estate_b.estate_id)).status_code == 403
    assert (await call(w.hoa_admin_a, 'POST', '/authorities', foreign)).status_code == 404
    _, request = await authorize_and_request(w, call)
    ident = request['request_id']
    assert (await call(w.resident_a2, 'GET', f'/requests/{ident}')).status_code == 404
    assert (await call(w.hoa_admin_b, 'GET', f'/requests/{ident}', estate_id=w.estate_b.estate_id)).status_code == 404
    assert (await call(w.resident_b1, 'GET', f'/requests/{ident}')).status_code == 403
    assert (await call(w.resident_a2, 'GET', '/requests')).json()['total'] == 0
    assert (await call(w.hoa_admin_a, 'POST', f'/requests/{ident}/decision', {
        'decision': 'approved', 'agent_id': w.hoa_admin_b.user_id, 'reason': 'Invalid foreign agent'})).status_code == 403
    assert (await call(w.resident_a1, 'POST', '/requests', body)).status_code == 409


async def test_revocation_withdraws_listing_and_cancels_request(market):
    w, call = market
    authority, request, listing = await approved_listing(w, call)
    result = await call(w.hoa_admin_a, 'POST', f"/authorities/{authority['authority_id']}/revoke", {'reason': 'Owner mandate withdrawn'})
    assert result.status_code == 200, result.text
    assert result.json()['revoked_at'] is not None
    assert (await call(w.resident_a1, 'GET', f"/requests/{request['request_id']}")).json()['status'] == 'cancelled'
    assert (await call(w.resident_a1, 'GET', f"/listings/{listing['listing_id']}")).json()['status'] == 'withdrawn'
    assert (await call(w.provider_user_a, 'POST', f"/listings/{listing['listing_id']}/actions", {
        'action': 'publish', 'expected_version': 2, 'reason': 'Old mandate'})).status_code == 409


async def test_pending_cancellation_and_rejection_are_final(market):
    w, call = market
    _, request = await authorize_and_request(w, call)
    path = f"/requests/{request['request_id']}"
    cancelled = await call(w.resident_a1, 'POST', path + '/cancel', {'reason': 'Owner changed plans'})
    assert cancelled.status_code == 200 and cancelled.json()['status'] == 'cancelled'
    assert (await call(w.hoa_admin_a, 'POST', path + '/decision', {
        'decision': 'approved', 'reason': 'Too late', 'agent_id': w.provider_user_a.user_id})).status_code == 409
    new = await call(w.resident_a1, 'POST', '/requests', {
        'property_id': w.property_a1.unit_id, 'purpose': 'rent', 'requested_price': '11000'})
    rejected = await call(w.hoa_admin_a, 'POST', f"/requests/{new.json()['request_id']}/decision", {
        'decision': 'rejected', 'reason': 'Consent documentation incomplete'})
    assert rejected.status_code == 200 and rejected.json()['status'] == 'rejected'


async def test_concurrent_price_changes_cannot_lose_history(market, test_db_sessionmaker):
    w, call = market
    _, _, listing = await approved_listing(w, call)
    ident = listing['listing_id']

    async def revise(amount):
        async with test_db_sessionmaker() as session:
            return await MarketService(session).change_price(w.estate_a.estate_id, ident,
                PriceChange(asking_price=amount, expected_version=1, reason='Concurrent owner instruction'), w.provider_user_a)

    outcomes = await asyncio.gather(revise('1390000'), revise('1410000'), return_exceptions=True)
    assert sum(isinstance(result, ConflictException) for result in outcomes) == 1
    assert sum(not isinstance(result, BaseException) for result in outcomes) == 1
    history = (await call(w.resident_a1, 'GET', f'/listings/{ident}/price-history')).json()
    assert history['total'] == 2
    assert [row['listing_version'] for row in history['items']] == [2, 1]


async def test_audit_failure_rolls_back_price_and_history(market, test_db_sessionmaker, monkeypatch):
    w, call = market
    _, _, listing = await approved_listing(w, call)
    ident = listing['listing_id']
    async with test_db_sessionmaker() as session:
        service = MarketService(session)
        original_add = service._repo.add

        async def failing_audit(model, **values):
            if model is MarketEvent:
                raise RuntimeError('Synthetic audit storage failure')
            return await original_add(model, **values)

        monkeypatch.setattr(service._repo, 'add', failing_audit)
        with pytest.raises(RuntimeError, match='Synthetic audit'):
            await service.change_price(w.estate_a.estate_id, ident,
                PriceChange(asking_price='1400000', expected_version=1, reason='Atomicity acceptance'), w.provider_user_a)
        await session.rollback()
    unchanged = (await call(w.resident_a1, 'GET', f'/listings/{ident}')).json()
    assert unchanged['asking_price'] == listing['asking_price'] and unchanged['version'] == 1
    assert (await call(w.resident_a1, 'GET', f'/listings/{ident}/price-history')).json()['total'] == 1


async def test_agents_and_owners_cannot_finalize_or_bypass_approval(market):
    w, call = market
    _, request = await authorize_and_request(w, call)
    draft_body = {'request_id': request['request_id'], 'title': 'Test apartment',
                  'description': 'Fictional apartment description', 'asking_price': '1350000'}
    assert (await call(w.hoa_admin_a, 'POST', '/listings', draft_body)).status_code == 409
    assert (await call(w.resident_a1, 'POST', f"/requests/{request['request_id']}/decision", {
        'decision': 'approved', 'agent_id': w.provider_user_a.user_id, 'reason': 'Self approval'})).status_code == 403
    await call(w.hoa_admin_a, 'POST', f"/requests/{request['request_id']}/decision", {
        'decision': 'approved', 'agent_id': w.provider_user_a.user_id, 'reason': 'Verified'})
    assert (await call(w.resident_a1, 'POST', '/listings', draft_body)).status_code == 403
    listing = (await call(w.provider_user_a, 'POST', '/listings', draft_body)).json()
    ident = listing['listing_id']
    completion = {'actual_amount': '1330000', 'effective_date': date.today().isoformat(),
                  'expected_version': 1, 'reference': 'Test completion'}
    assert (await call(w.provider_user_a, 'POST', f'/listings/{ident}/complete', completion)).status_code == 403
    assert (await call(w.hoa_admin_a, 'POST', f'/listings/{ident}/complete', completion)).status_code == 409
    await call(w.provider_user_a, 'POST', f'/listings/{ident}/actions', {
        'action': 'publish', 'expected_version': 1, 'reason': 'Verified'})
    assert (await call(w.hoa_admin_a, 'POST', f'/listings/{ident}/complete', completion | {
        'expected_version': 2, 'effective_date': (date.today() + timedelta(days=1)).isoformat()})).status_code == 400
    assert (await call(w.hoa_admin_a, 'GET', '/sales')).json()['total'] == 0


async def test_current_routes_require_auth_and_validate_boundary_inputs(market):
    w, call = market
    assert (await call(w.resident_a1, 'GET', '/listings', size=101)).status_code == 422
    assert (await call(w.resident_a1, 'GET', '/listings/2147483648')).status_code == 422
    assert (await call(w.resident_a1, 'POST', '/requests', {
        'property_id': w.property_a1.unit_id, 'purpose': 'sale', 'requested_price': '1',
        'status': 'approved'})).status_code == 422
    app.dependency_overrides.pop(get_current_user, None)
    assert (await call(None, 'GET', '/sales')).status_code == 401


async def test_listing_content_edit_is_versioned_and_cannot_smuggle_price(market):
    w, call = market
    _, _, listing = await approved_listing(w, call)
    path = f"/listings/{listing['listing_id']}"
    content = {'title': 'Updated apartment title', 'description': 'Corrected approved description.',
               'expected_version': 1, 'reason': 'Corrected owner-approved marketing copy'}
    updated = await call(w.provider_user_a, 'PATCH', path, content)
    assert updated.status_code == 200, updated.text
    assert updated.json()['title'] == content['title'] and updated.json()['version'] == 2
    assert updated.json()['asking_price'] == listing['asking_price']
    assert (await call(w.provider_user_a, 'PATCH', path, content | {'expected_version': 2, 'asking_price': '1'})).status_code == 422
    assert (await call(w.resident_a1, 'PATCH', path, content | {'expected_version': 2})).status_code == 403
