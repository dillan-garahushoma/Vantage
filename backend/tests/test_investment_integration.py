"""Real PostgreSQL persistence/isolation acceptance; never silently replace with mocks."""
import pytest

from app.core.exceptions import ForbiddenException, NotFoundException
from app.property.schemas.investment import InvestmentScenarioCreate
from app.property.services.investment_calculator import musgrave_preset
from app.property.services.investment_service import InvestmentService
from tests.factories import build_two_estate_world

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_snapshot_is_visible_in_fresh_database_session(db_session, test_db_sessionmaker):
    world = await build_two_estate_world(db_session)
    payload = InvestmentScenarioCreate(estate_id=world.estate_a.estate_id, property_id=world.property_a1.unit_id,
                                       name='Fictional Musgrave assumptions', assumptions=musgrave_preset())
    saved = await InvestmentService(db_session).save(payload, world.resident_a1)
    async with test_db_sessionmaker() as fresh:
        loaded = await InvestmentService(fresh).get(saved.scenario_id, world.resident_a1, estate_id=world.estate_a.estate_id)
        assert loaded == saved


async def test_real_database_denies_other_owner_and_other_estate(db_session):
    world = await build_two_estate_world(db_session)
    service = InvestmentService(db_session)
    saved = await service.save(InvestmentScenarioCreate(estate_id=world.estate_a.estate_id, property_id=world.property_a1.unit_id,
                                                       name='Private assumptions', assumptions=musgrave_preset()), world.resident_a1)
    with pytest.raises(NotFoundException):
        await service.get(saved.scenario_id, world.hoa_admin_a, estate_id=world.estate_a.estate_id)
    with pytest.raises(ForbiddenException):
        await service.get(saved.scenario_id, world.resident_b1, estate_id=world.estate_a.estate_id)
    with pytest.raises(NotFoundException):
        await service.get(saved.scenario_id, world.resident_b1, estate_id=world.estate_b.estate_id)


async def test_revision_adds_new_row_and_preserves_prior_snapshot(db_session):
    world = await build_two_estate_world(db_session)
    service = InvestmentService(db_session)
    payload = InvestmentScenarioCreate(estate_id=world.estate_a.estate_id, property_id=world.property_a1.unit_id,
                                       name='Original', assumptions=musgrave_preset())
    first = await service.save(payload, world.resident_a1)
    second = await service.save(InvestmentScenarioCreate(estate_id=payload.estate_id, property_id=payload.property_id,
                                                        name='Lower rent', assumptions=musgrave_preset() | {'monthly_rent': '9000'},
                                                        revision_of=first.scenario_id), world.resident_a1)
    assert first.scenario_id != second.scenario_id
    assert second.revision_of == first.scenario_id
    assert (await service.get(first.scenario_id, world.resident_a1, estate_id=payload.estate_id)) == first
    listed = await service.list_mine(world.resident_a1, estate_id=payload.estate_id, page=1, size=20)
    assert listed.total == 2
