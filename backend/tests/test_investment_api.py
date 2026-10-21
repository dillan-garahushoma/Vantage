"""Real HTTP/DTO/error contracts backed by explicit in-memory test doubles."""
from datetime import datetime, timezone
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import ForbiddenException
from app.db.session import get_db
from app.identity.api.dependencies import get_current_user
from app.identity.services.estate_authorization_service import EstateAccess
from app.main import app
from app.property.api import investments
from app.property.services.investment_calculator import musgrave_preset
from app.property.services.investment_service import InvestmentService


@pytest.fixture
def client(monkeypatch):
    db = NS(commit=AsyncMock(), rollback=AsyncMock())
    service = InvestmentService(db)
    rows = {}

    async def access(actor, estate_id):
        if estate_id != 1:
            raise ForbiddenException('Not a member.')
        return EstateAccess(actor.user_id, 1, frozenset({'investor'}), frozenset(), False, False)

    async def property_(**kwargs):
        return NS(unit_id=2, estate_id=1) if kwargs == {'unit_id': 2, 'estate_id': 1} else None

    async def add(**values):
        row = NS(scenario_id=len(rows)+1, created_at=datetime.now(timezone.utc), **values)
        rows[row.scenario_id] = row
        return row

    async def get_owned(*, scenario_id, estate_id, owner_id):
        row = rows.get(scenario_id)
        return row if row and row.estate_id == estate_id and row.owner_id == owner_id else None

    service._authorization.resolve_access = access
    service._properties.get_by_id_in_estate = property_
    service._repo = NS(add=add, get_owned=get_owned,
                       list_owned=AsyncMock(side_effect=lambda **kw: [row for row in rows.values() if row.owner_id == kw['owner_id']][kw['offset']:kw['offset']+kw['limit']]),
                       count_owned=AsyncMock(side_effect=lambda **kw: sum(row.owner_id == kw['owner_id'] for row in rows.values())))
    monkeypatch.setattr(investments, 'InvestmentService', lambda _: service)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: NS(user_id=7, role='investor')
    with TestClient(app) as http:
        yield http
    app.dependency_overrides.clear()


def body(**changes):
    return dict(estate_id=1, property_id=2, name='Musgrave example', assumptions=musgrave_preset()) | changes


def test_preset_and_preview_do_not_create_records(client):
    preset = client.get('/api/v1/investment-scenarios/presets/musgrave?estate_id=1&property_id=2')
    assert preset.status_code == 200 and preset.json()['data_source'] == 'fictional_musgrave'
    preview = client.post('/api/v1/investment-scenarios/calculate', json={key: value for key, value in body().items() if key != 'name'})
    assert preview.status_code == 200
    assert preview.json()['gross_yield_percent'] == '10.222222'
    assert client.get('/api/v1/investment-scenarios?estate_id=1').json()['total'] == 0


def test_create_revision_read_and_paginate_with_immutable_prior_result(client):
    created = client.post('/api/v1/investment-scenarios', json=body())
    assert created.status_code == 201
    original = created.json()
    assumptions = musgrave_preset() | {'monthly_rent': '10000'}
    revised = client.post('/api/v1/investment-scenarios', json=body(revision_of=original['scenario_id'], assumptions=assumptions))
    assert revised.status_code == 201 and revised.json()['revision_of'] == original['scenario_id']
    assert revised.json()['result']['net_yield_percent'] != original['result']['net_yield_percent']
    assert client.get(f"/api/v1/investment-scenarios/{original['scenario_id']}?estate_id=1").json() == original
    page = client.get('/api/v1/investment-scenarios?estate_id=1&size=1&page=2').json()
    assert (page['total'], page['pages'], len(page['items'])) == (2, 2, 1)
    assert client.patch('/api/v1/investment-scenarios/1?estate_id=1', json={}).status_code == 405
    assert client.delete('/api/v1/investment-scenarios/1?estate_id=1').status_code == 405


def test_no_admin_override_for_other_users_financial_snapshots(client):
    client.post('/api/v1/investment-scenarios', json=body())
    app.dependency_overrides[get_current_user] = lambda: NS(user_id=8, role='hoa_admin')
    response = client.get('/api/v1/investment-scenarios/1?estate_id=1')
    assert response.status_code == 404
    assert client.get('/api/v1/investment-scenarios?estate_id=1').json()['total'] == 0


@pytest.mark.parametrize('changes,status', [({'estate_id': 99}, 403), ({'property_id': 99}, 404), ({'owner_id': 8}, 422), ({'assumptions': musgrave_preset() | {'purchase_price': 'NaN'}}, 422), ({'estate_id': 2147483648}, 422), ({'name': '\x00'}, 422)])
def test_http_boundary_errors_use_standard_envelope(client, changes, status):
    response = client.post('/api/v1/investment-scenarios', json=body(**changes))
    assert response.status_code == status
    assert 'request_id' in response.json()['detail']
    assert response.headers.get('X-Request-ID')


def test_endpoints_require_authentication(client):
    app.dependency_overrides.pop(get_current_user)
    response = client.get('/api/v1/investment-scenarios?estate_id=1')
    assert response.status_code == 401


def test_invalid_page_size_is_rejected(client):
    assert client.get('/api/v1/investment-scenarios?estate_id=1&size=101').status_code == 422
