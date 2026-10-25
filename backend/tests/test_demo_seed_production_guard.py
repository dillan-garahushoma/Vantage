"""Demo data must never be provisioned into an operational database."""
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.seed_demo import SeedGuardError, seed_demo, validate_seed_target


@pytest.mark.parametrize('database', ['neondb', 'valora_db', 'valora_pilot', 'valora_prod_demo'])
def test_common_operational_database_names_are_never_seed_targets(database):
    with pytest.raises(SeedGuardError):
        validate_seed_target(database, expect_database=database)


@pytest.mark.parametrize('environment', ['production', 'staging', 'pilot'])
def test_operational_environment_refuses_even_a_demo_database(environment):
    with pytest.raises(SeedGuardError, match='development or test'):
        validate_seed_target('valora_demo_test', expect_database='valora_demo_test', environment=environment)


@pytest.mark.parametrize('environment', ['development', 'test'])
def test_explicit_demo_database_is_available_for_local_testing(environment):
    validate_seed_target('valora_demo_test', expect_database='valora_demo_test', environment=environment)


@pytest.mark.asyncio
async def test_seeder_checks_the_runtime_environment_before_writing(monkeypatch):
    monkeypatch.setattr('app.core.config.get_settings', lambda: SimpleNamespace(ENVIRONMENT='production'))
    monkeypatch.setattr('app.seed_demo.current_database_name', AsyncMock(return_value='valora_demo_test'))
    database = SimpleNamespace(execute=AsyncMock())
    with pytest.raises(SeedGuardError, match='development or test'):
        await seed_demo(database, expect_database='valora_demo_test')
    database.execute.assert_not_awaited()
