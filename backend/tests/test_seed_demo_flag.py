"""The demo seeder must flag the estate it creates, and must be safe to re-run.

The earlier version of this file ran the seeder against a fake in-memory session.
The seeder now guards its target database, drives the real photo pipeline and the
real Living Score engine, and is therefore exercised against the throwaway
database — the only place a real run means anything. Its guard means the database
name must contain "demo"; the integration fixture additionally demands "test".
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import func, select

from app.property.models.estate import Estate
from app.seed_demo import DEMO_ESTATE_NAME, seed_demo

pytestmark = pytest.mark.integration


def expected_database() -> str:
    """The name of the database the throwaway session is actually connected to."""
    url = os.environ.get("TEST_DATABASE_URL", "")
    return url.rsplit("/", 1)[-1].split("?")[0]


@pytest.fixture(autouse=True)
def requires_demo_database():
    name = expected_database()
    if "demo" not in name.lower():
        pytest.skip(
            "the demo seeder refuses a database whose name does not contain 'demo'; "
            f"TEST_DATABASE_URL names {name!r}"
        )


@pytest.mark.asyncio
async def test_seeded_estate_is_operational_data_not_demo_data(db_session, tmp_path) -> None:
    summary = await seed_demo(
        db_session, expect_database=expected_database(), upload_dir=tmp_path
    )

    assert summary["created"] is True
    estate = (
        await db_session.execute(select(Estate).where(Estate.name == DEMO_ESTATE_NAME))
    ).scalar_one()
    assert estate.is_demo is True
    assert estate.is_public is False
    assert estate.show_living_score is False


@pytest.mark.asyncio
async def test_seeding_an_existing_demo_estate_changes_nothing(db_session, tmp_path) -> None:
    first = await seed_demo(
        db_session, expect_database=expected_database(), upload_dir=tmp_path
    )
    assert first["created"] is True

    second = await seed_demo(
        db_session, expect_database=expected_database(), upload_dir=tmp_path
    )

    assert second["created"] is False
    assert "already exist" in str(second["message"])
    estates = await db_session.execute(
        select(func.count()).select_from(Estate).where(Estate.name == DEMO_ESTATE_NAME)
    )
    assert estates.scalar_one() == 1
