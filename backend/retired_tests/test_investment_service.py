"""Privacy, estate boundary and immutable write behavior before implementation."""
from datetime import datetime, timezone
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ForbiddenException, NotFoundException
from app.identity.services.estate_authorization_service import EstateAccess
from app.property.schemas.investment import InvestmentCalculationRequest, InvestmentScenarioCreate
from app.property.services.investment_calculator import musgrave_preset
from app.property.services.investment_service import InvestmentService


def service(role='investor', memberships=frozenset({'investor'}), property_ids=frozenset()):
    db = NS(commit=AsyncMock(), rollback=AsyncMock())
    instance = InvestmentService(db)
    actor = NS(user_id=7, role=role)
    access = EstateAccess(7, 1, memberships, property_ids, role == 'hoa_admin' and 'hoa_admin' in memberships, False)
    instance._authorization.resolve_access = AsyncMock(return_value=access)
    instance._properties.get_by_id_in_estate = AsyncMock(return_value=NS(unit_id=2, estate_id=1))
    instance._repo = NS(add=AsyncMock(), get_owned=AsyncMock(), list_owned=AsyncMock(), count_owned=AsyncMock())
    return instance, actor, db


def request(**changes):
    return InvestmentScenarioCreate.model_validate(dict(estate_id=1, property_id=2, name='Musgrave scenario', assumptions=musgrave_preset()) | changes)


@pytest.mark.asyncio
async def test_preview_requires_resolved_membership_then_scoped_property():
    instance, actor, db = service()
    result = await instance.preview(InvestmentCalculationRequest.model_validate(request().model_dump(exclude={'name', 'revision_of'})), actor)
    assert result.gross_yield_percent > 0
    instance._authorization.resolve_access.assert_awaited_once_with(actor, 1)
    instance._properties.get_by_id_in_estate.assert_awaited_once_with(unit_id=2, estate_id=1)
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_nonmember_cannot_probe_property():
    instance, actor, _ = service()
    instance._authorization.resolve_access.side_effect = ForbiddenException()
    with pytest.raises(ForbiddenException):
        await instance.preset(actor, estate_id=1, property_id=2)
    instance._properties.get_by_id_in_estate.assert_not_awaited()


@pytest.mark.asyncio
async def test_property_in_another_estate_is_not_found():
    instance, actor, _ = service()
    instance._properties.get_by_id_in_estate.return_value = None
    with pytest.raises(NotFoundException):
        await instance.preset(actor, estate_id=1, property_id=99)


@pytest.mark.asyncio
@pytest.mark.parametrize('role,membership', [('hoa_admin', 'resident'), ('investor', 'resident'), ('estate_agent', 'resident'), ('service_provider', 'service_provider')])
async def test_global_role_does_not_bypass_estate_capability(role, membership):
    instance, actor, _ = service(role, frozenset({membership}))
    with pytest.raises(ForbiddenException):
        await instance.preset(actor, estate_id=1, property_id=2)


@pytest.mark.asyncio
async def test_resident_may_model_own_linked_unit_but_not_another():
    instance, actor, _ = service('resident', frozenset({'resident'}), frozenset({2}))
    assert (await instance.preset(actor, estate_id=1, property_id=2)).data_source == 'fictional_musgrave'
    with pytest.raises(ForbiddenException):
        await instance.preset(actor, estate_id=1, property_id=3)


@pytest.mark.asyncio
async def test_save_persists_server_result_commits_once_and_keeps_snapshot():
    instance, actor, db = service()
    async def add(**values):
        return NS(scenario_id=12, created_at=datetime.now(timezone.utc), **values)
    instance._repo.add.side_effect = add
    payload = request()
    response = await instance.save(payload, actor)
    assert response.scenario_id == 12
    assert response.result.formula_version == response.formula_version
    assert response.assumptions == payload.assumptions
    assert instance._repo.add.call_args.kwargs['owner_id'] == 7
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_write_rolls_back_and_never_returns_success():
    instance, actor, db = service()
    instance._repo.add.side_effect = RuntimeError('database failure')
    with pytest.raises(RuntimeError):
        await instance.save(request(), actor)
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_revision_cannot_reference_another_users_or_another_units_scenario():
    instance, actor, db = service()
    instance._repo.get_owned.return_value = None
    with pytest.raises(NotFoundException):
        await instance.save(request(revision_of=42), actor)
    instance._repo.get_owned.assert_awaited_once_with(scenario_id=42, estate_id=1, owner_id=7)
    db.commit.assert_not_awaited()
    instance._repo.get_owned.return_value = NS(property_id=999)
    with pytest.raises(NotFoundException):
        await instance.save(request(revision_of=42), actor)


@pytest.mark.asyncio
async def test_admin_has_no_override_to_read_someone_elses_private_scenario():
    instance, actor, _ = service('hoa_admin', frozenset({'hoa_admin'}))
    instance._repo.get_owned.return_value = None
    with pytest.raises(NotFoundException):
        await instance.get(42, actor, estate_id=1)
    instance._repo.get_owned.assert_awaited_once_with(scenario_id=42, estate_id=1, owner_id=7)


@pytest.mark.asyncio
async def test_listing_is_owner_and_estate_scoped_with_true_count():
    instance, actor, _ = service()
    instance._repo.list_owned.return_value = []
    instance._repo.count_owned.return_value = 142
    result = await instance.list_mine(actor, estate_id=1, page=2, size=20)
    assert result.total == 142 and result.pages == 8
    instance._repo.list_owned.assert_awaited_once_with(estate_id=1, owner_id=7, offset=20, limit=20)


@pytest.mark.asyncio
async def test_saved_scenario_is_not_recomputed_after_input_or_formula_changes():
    instance, actor, _ = service()
    payload = request()
    instance._repo.add.side_effect = lambda **values: NS(scenario_id=12, created_at=datetime.now(timezone.utc), **values)
    saved = await instance.save(payload, actor)
    instance._repo.get_owned.return_value = NS(**saved.model_dump(), owner_id=7)
    actual = await instance.get(12, actor, estate_id=1)
    assert actual == saved
