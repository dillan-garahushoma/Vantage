"""P4 — the demonstration estate: guards, content, real photos, real scores.

Three promises the demo must keep, each asserted here:

* **It cannot land in the wrong database.** The guard is checked against the live
  connection and refuses before anything is written.
* **It is deterministic and idempotent.** A second run changes nothing: no second
  estate, no extra photos, no extra snapshots.
* **Nothing is faked.** Photographs go through the real upload pipeline (so they
  are re-encoded JPEGs with no EXIF), Living Score snapshots are produced by the
  real engine, and no AI output is ever seeded.

Integration tests need a throwaway database whose name contains both "demo" (the
seeder's guard) and "test" (the harness's guard).
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.analytics.models.living_score_snapshot import LivingScoreSnapshot
from app.common.enums import ComplaintStatus, UserRole
from app.community.models.announcement import Announcement
from app.community.models.complaint import Complaint
from app.community.models.complaint_event import ComplaintEvent
from app.community.models.maintenance_work_order import MaintenanceworkOrder
from app.community.models.security_incident import SecurityIncident
from app.identity.models.estate_membership import EstateMembership
from app.identity.models.user import User
from app.property.domain.photo_pipeline import photo_path
from app.property.models.estate import Estate
from app.property.models.estate_photo import EstatePhoto
from app.property.models.property import Property
from app.providers.models.service_provider import ServiceProvider
from app.seed_demo import (
    DEMO_ESTATE_NAME,
    DEMO_HISTORY_DAYS,
    COMPLEX_CONFIGS,
    DEMO_SCORE_AS_OF_OFFSETS,
    SeedGuardError,
    count_demo_ai_rows,
    seed_demo,
    validate_seed_target,
)

pytestmark = pytest.mark.integration


def expected_database() -> str:
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


async def _count(db, model) -> int:
    result = await db.execute(select(func.count()).select_from(model))
    return int(result.scalar_one())


# --------------------------------------------------------------------------- #
# Guards
# --------------------------------------------------------------------------- #
def test_the_guard_refuses_a_database_that_is_not_a_demo_database() -> None:
    with pytest.raises(SeedGuardError, match="must contain 'demo'"):
        validate_seed_target("valora_pilot_dev", expect_database="valora_pilot_dev")


def test_the_guard_refuses_a_database_other_than_the_expected_one() -> None:
    with pytest.raises(SeedGuardError, match="does not match the connected database"):
        validate_seed_target("valora_demo", expect_database="valora_demo_test")


def test_the_guard_accepts_the_named_demo_database() -> None:
    validate_seed_target("valora_demo", expect_database="valora_demo")
    validate_seed_target("valora_demo_test_20261012", expect_database="valora_demo_test_20261012")


@pytest.mark.asyncio
async def test_a_refused_seed_writes_nothing(db_session, tmp_path) -> None:
    with pytest.raises(SeedGuardError):
        await seed_demo(db_session, expect_database="some_other_database", upload_dir=tmp_path)

    assert await _count(db_session, Estate) == 0
    assert await _count(db_session, User) == 0
    assert list(tmp_path.iterdir()) == []


# --------------------------------------------------------------------------- #
# Content
# --------------------------------------------------------------------------- #
@pytest.fixture
def image_sources(tmp_path):
    """Real synthetic JPEG inputs; tests do not depend on untracked demo media."""
    from PIL import Image

    directory = tmp_path / 'source-images'
    directory.mkdir()
    for config in COMPLEX_CONFIGS:
        for filename, _caption in config['image_assets']:
            image = Image.new('RGB', (800, 600), color=(90, 120, 150))
            exif = image.getexif()
            exif[270] = 'Synthetic acceptance image; strip this metadata'
            image.save(directory / filename, format='JPEG', exif=exif)
    return directory


@pytest_asyncio.fixture
async def seeded(db_session, tmp_path, image_sources):
    """Current five-estate demonstration portfolio, seeded once per test."""
    summary = await seed_demo(
        db_session, expect_database=expected_database(), upload_dir=tmp_path, image_dir=image_sources
    )
    assert summary["created"] is True
    return summary, db_session, tmp_path


@pytest.mark.asyncio
async def test_the_demo_world_has_the_people_the_brief_asks_for(seeded) -> None:
    summary, db, _tmp = seeded

    assert summary["properties"] == 24
    assert len(summary['estates']) == 5
    assert await _count(db, Property) == 90

    roles = (await db.execute(select(User.role, func.count()).group_by(User.role))).all()
    by_role = {role: count for role, count in roles}
    assert by_role[UserRole.hoa_admin.value] == 5
    assert by_role[UserRole.resident.value] == 81
    assert by_role[UserRole.service_provider.value] == 10

    # Both providers are linked to a provider profile *and* are members of the
    # estate: that is what makes them assignable to work.
    providers = (
        await db.execute(select(ServiceProvider).order_by(ServiceProvider.provider_id))
    ).scalars().all()
    assert len(providers) == 10
    assert all(provider.user_id is not None for provider in providers)

    linked_ids = {provider.user_id for provider in providers}
    member_ids = {
        row
        for (row,) in (
            await db.execute(
                select(EstateMembership.user_id).where(
                    EstateMembership.membership_role == UserRole.service_provider.value
                )
            )
        ).all()
    }
    assert linked_ids == member_ids

    # every demo login lives on the documented domain
    emails = [email for (email,) in (await db.execute(select(User.email))).all()]
    assert all(email.endswith("@example.com") for email in emails)


@pytest.mark.asyncio
async def test_the_demo_history_matches_the_five_operational_profiles(seeded) -> None:
    _summary, db, _tmp = seeded

    assert await _count(db, Complaint) == 154
    statuses = {
        status for (status,) in (await db.execute(select(Complaint.status))).all()
    }
    assert statuses == {
        ComplaintStatus.submitted.value,
        ComplaintStatus.assigned.value,
        ComplaintStatus.in_progress.value,
        ComplaintStatus.resolved.value,
        ComplaintStatus.rated.value,
    }

    # Every complaint has a "submitted" event at its own created_at, and any
    # further status its row claims has an event carrying the same timestamp.
    events = (
        await db.execute(
            select(ComplaintEvent.complaint_id, ComplaintEvent.event_type, ComplaintEvent.occurred_at)
        )
    ).all()
    by_complaint: dict[int, dict[str, object]] = {}
    for complaint_id, event_type, occurred_at in events:
        by_complaint.setdefault(complaint_id, {})[event_type] = occurred_at

    complaints = (await db.execute(select(Complaint))).scalars().all()
    assert set(by_complaint) == {complaint.complaint_id for complaint in complaints}
    for complaint in complaints:
        timeline = by_complaint[complaint.complaint_id]
        assert timeline["submitted"] == complaint.created_at
        if complaint.reviewed_at is not None:
            assert timeline["reviewed"] == complaint.reviewed_at
        if complaint.resolved_at is not None:
            assert timeline["resolved"] == complaint.resolved_at
        if complaint.status == ComplaintStatus.rated.value:
            assert "rated" in timeline

    # Work orders, ratings and incidents exist and line up with the complaints.
    assert await _count(db, MaintenanceworkOrder) > 20
    rated = (
        await db.execute(
            select(func.count()).select_from(MaintenanceworkOrder).where(
                MaintenanceworkOrder.resident_rating.is_not(None)
            )
        )
    ).scalar_one()
    assert int(rated) >= 5
    assert await _count(db, SecurityIncident) == 27
    assert await _count(db, Announcement) == 13


@pytest.mark.asyncio
async def test_placeholder_photographs_are_stored_through_the_real_pipeline(seeded) -> None:
    summary, db, upload_dir = seeded

    rows = (await db.execute(select(EstatePhoto))).scalars().all()
    assert len(rows) == 20
    captions = {caption for config in COMPLEX_CONFIGS for _filename, caption in config['image_assets']}

    from PIL import Image

    for row in rows:
        full = photo_path(upload_dir, row.public_id)
        thumb = photo_path(upload_dir, row.public_id, thumb=True)
        assert full.exists() and thumb.exists()
        assert full.stat().st_size == row.bytes
        assert row.caption in captions

        with Image.open(full) as image:
            # re-encoded by the pipeline: no EXIF at all, and bounded to 1920 px
            assert not image.getexif()
            assert max(image.size) <= 1920
        with Image.open(thumb) as image:
            assert max(image.size) <= 480

    assert sum(estate['photos'] for estate in summary['estates']) == 20
    assert all(sum(row.estate_id == estate['estate_id'] for row in rows) == 4 for estate in summary['estates'])


@pytest.mark.asyncio
async def test_the_estate_is_backdated_and_scores_are_real_snapshots(seeded) -> None:
    summary, db, _tmp = seeded

    estate = (
        await db.execute(select(Estate).where(Estate.name == DEMO_ESTATE_NAME))
    ).scalar_one()
    now = (await db.execute(select(func.now()))).scalar_one()
    age_days = (now - estate.created_at).days
    assert age_days >= 60, f"the brief asks for at least 60 days of history, got {age_days}"
    assert DEMO_HISTORY_DAYS >= 60

    snapshots = (
        await db.execute(
            select(LivingScoreSnapshot)
            .where(LivingScoreSnapshot.estate_id == estate.estate_id)
            .order_by(LivingScoreSnapshot.as_of)
        )
    ).scalars().all()
    assert len(snapshots) == len(DEMO_SCORE_AS_OF_OFFSETS)

    # Every snapshot came out of the real engine, and the invariant the database
    # enforces holds: a scored snapshot has a number, an insufficient one does not.
    for snapshot in snapshots:
        assert snapshot.engine_version == "1.0.0"
        assert (snapshot.status == "scored") == (snapshot.overall_score is not None)

    # The history really is old -> new, and the newest is the current picture.
    assert [snapshot.as_of for snapshot in snapshots] == sorted(
        snapshot.as_of for snapshot in snapshots
    )
    assert (now - snapshots[-1].as_of).total_seconds() < 3600
    assert snapshots[-1].status == "scored"
    assert summary["scores"][-1]["engine_version"] == "1.0.0"


@pytest.mark.asyncio
async def test_no_ai_output_is_ever_seeded(seeded) -> None:
    _summary, db, _tmp = seeded

    assert await count_demo_ai_rows(db) == {"ai_insights": 0, "ai_suggestions": 0}


@pytest.mark.asyncio
async def test_running_the_seed_twice_adds_nothing(db_session, tmp_path, image_sources) -> None:
    first = await seed_demo(
        db_session, expect_database=expected_database(), upload_dir=tmp_path, image_dir=image_sources
    )
    counts = {
        model: await _count(db_session, model)
        for model in (User, Property, Complaint, ComplaintEvent, MaintenanceworkOrder, EstatePhoto, LivingScoreSnapshot)
    }

    second = await seed_demo(
        db_session, expect_database=expected_database(), upload_dir=tmp_path, image_dir=image_sources
    )

    assert first["created"] is True and second["created"] is False
    for model, before in counts.items():
        assert await _count(db_session, model) == before, f"{model.__name__} grew on a re-run"
    assert len(list(tmp_path.glob("*.jpg"))) == 40
