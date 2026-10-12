"""Health brief over HTTP against a real database (BATCH AI-4).

Needs `TEST_DATABASE_URL` and auto-skips without it. This is the only place the
tenant boundary, the real constraints and the stored-row round trip are proven:
the facts cross into JSONB and come back out through the response DTO.

The AI layer is off in every test here (the default), which is the point: the
product answers with the deterministic template and stores nothing.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.analytics.ai.brief_facts import COMPONENT_KEYS, BriefFacts, build_brief_facts
from app.analytics.ai.brief_output import PROMPT_VERSION
from app.analytics.models.ai_call_event import AICallEvent
from app.analytics.models.ai_insight import AIInsight
from app.analytics.models.ai_insight_feedback import AIInsightFeedback
from app.analytics.models.living_score_snapshot import LivingScoreSnapshot
from app.common.enums import UserRole
from app.core.config import get_settings
from app.core.security import create_access_token

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def ai_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the AI layer off for every test in this file.

    A developer's `backend/.env` may enable AI with a real provider, and these
    tests must never contact one: without this, "generate with AI off" would make
    a live, billed provider call on that machine. `get_settings` is cached, so the
    cache is cleared around the patch.
    """
    for name, value in (
        ("AI_ENABLED", "false"),
        ("AI_INSIGHTS_ENABLED", "false"),
        ("AI_TRIAGE_ENABLED", "false"),
        ("AI_PERSONAL_DATA_ALLOWED", "false"),
    ):
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def ai_fake(ai_off: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Turn the layer on with the deterministic in-process provider.

    Runs after `ai_off`, and uses only the fake adapter from AI-1, so the whole
    HTTP -> service -> guard -> ledger -> database path is exercised with no
    network and no key.
    """
    for name, value in (
        ("AI_ENABLED", "true"),
        ("AI_INSIGHTS_ENABLED", "true"),
        ("AI_PROVIDER", "fake"),
        ("AI_MODEL", "fake-deterministic"),
    ):
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()

API_PREFIX = "/api/v1/analytics/health-brief"
BRIEF_PATH = API_PREFIX
FEEDBACK_PATH = f"{API_PREFIX}/{{insight_id}}/feedback"

AS_OF = datetime(2026, 10, 11, 9, 0, tzinfo=timezone.utc)

SCORES = {
    "resolution": "98.85",
    "frequency": "60.00",
    "security": "93.33",
    "satisfaction": "83.33",
    "infrastructure": "75.00",
}
WEIGHTS = {
    "resolution": "0.30",
    "frequency": "0.25",
    "security": "0.20",
    "satisfaction": "0.15",
    "infrastructure": "0.10",
}
RAW_INPUTS = {
    "resolution": {"avg_resolution_days": "1.33", "resolved_complaints": 3},
    "frequency": {"complaints_created": 4, "unit_count": 2, "coverage_days": 90},
    "security": {"incidents": 1, "coverage_days": 90, "unit_count": 2},
    "satisfaction": {"avg_rating": "4.33", "rated_count": 3},
    "infrastructure": {"work_orders_in_window": 4, "work_orders_completed": 3},
}

GROUNDED_OUTPUT = {
    "headline": "Living Score 83.32 out of 100",
    "summary": "Over 90 days the estate scored 83.32, with complaint frequency at 60.00.",
    "drivers": [
        {
            "component": "frequency",
            "direction": "stable",
            "statement": "Complaint frequency scored 60.00.",
        }
    ],
    "actions": [{"component": "frequency", "action": "Review repeat complaint sources."}],
}


def _bearer(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.user_id)})}"}


def _explanation() -> dict:
    components = [
        {
            "key": key,
            "weight": WEIGHTS[key],
            "status": "measured",
            "score": SCORES[key],
            "raw_inputs": RAW_INPUTS[key],
            "benchmark": "a benchmark",
            "contribution": "10.00",
            "lost_points": "1.00",
            "explanation": "the engine's own sentence",
            "recommendation": "Review this component.",
        }
        for key in COMPONENT_KEYS
    ]
    return {
        "engine_version": "1.0.0",
        "status": "scored",
        "overall_score": "83.32",
        "measured_weight": "1.00",
        "components": components,
        "drivers": components,
    }


async def _seed_estate(db, *, name: str, is_demo: bool = False):
    from app.property.models.estate import Estate

    estate = Estate(
        name=name,
        suburb="Centurion",
        city="Pretoria",
        province="Gauteng",
        is_demo=is_demo,
    )
    db.add(estate)
    await db.commit()
    return estate


async def _seed_user(db, *, email: str, role: str):
    from app.identity.models.user import User

    user = User(
        email=email,
        password_hash="x",
        full_name="Test Person",
        role=role,
    )
    db.add(user)
    await db.commit()
    return user


async def _seed_membership(db, *, user, estate, role: str):
    from app.identity.models.estate_membership import EstateMembership

    db.add(
        EstateMembership(
            user_id=user.user_id,
            estate_id=estate.estate_id,
            membership_role=role,
        )
    )
    await db.commit()


async def _seed_snapshot(db, *, estate, as_of: datetime = AS_OF, overall: str = "83.32"):
    snapshot = LivingScoreSnapshot(
        estate_id=estate.estate_id,
        engine_version="1.0.0",
        as_of=as_of,
        window_start=as_of - timedelta(days=90),
        calculated_by=None,
        status="scored",
        overall_score=Decimal(overall),
        measured_weight=Decimal("1.00"),
        resolution_score=Decimal(SCORES["resolution"]),
        frequency_score=Decimal(SCORES["frequency"]),
        security_score=Decimal(SCORES["security"]),
        satisfaction_score=Decimal(SCORES["satisfaction"]),
        infrastructure_score=Decimal(SCORES["infrastructure"]),
        inputs={},
        explanation=_explanation(),
    )
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)
    return snapshot


async def _seed_world(db, *, is_demo: bool = False):
    from types import SimpleNamespace

    estate = await _seed_estate(db, name="Zambezi Estate", is_demo=is_demo)
    other = await _seed_estate(db, name="Silver Lakes Estate")
    admin = await _seed_user(db, email="ai4_admin@valora.test", role=UserRole.hoa_admin.value)
    resident = await _seed_user(db, email="ai4_resident@valora.test", role=UserRole.resident.value)
    other_admin = await _seed_user(
        db, email="ai4_other_admin@valora.test", role=UserRole.hoa_admin.value
    )
    await _seed_membership(
        db, user=admin, estate=estate, role=UserRole.hoa_admin.value
    )
    await _seed_membership(
        db, user=resident, estate=estate, role=UserRole.resident.value
    )
    await _seed_membership(
        db, user=other_admin, estate=other, role=UserRole.hoa_admin.value
    )
    snapshot = await _seed_snapshot(db, estate=estate)
    return SimpleNamespace(
        estate=estate,
        other=other,
        admin=admin,
        resident=resident,
        other_admin=other_admin,
        snapshot=snapshot,
    )


async def _insert_insight(db, *, estate, snapshot, output: dict | None = None):
    facts = build_brief_facts(snapshot)
    row = AIInsight(
        estate_id=estate.estate_id,
        snapshot_id=snapshot.snapshot_id,
        kind="health_brief",
        prompt_version=PROMPT_VERSION,
        provider="stub",
        model="stub-model",
        facts=facts.model_dump(mode="json"),
        output=output or GROUNDED_OUTPUT,
        data_origin="live",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


# --------------------------------------------------------------------- reads


@pytest.mark.asyncio
async def test_a_member_reads_the_template_when_no_ai_insight_exists(
    db_session, async_client
) -> None:
    world = await _seed_world(db_session)

    response = await async_client.get(
        BRIEF_PATH,
        params={"estate_id": world.estate.estate_id},
        headers=_bearer(world.resident),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "template"
    assert body["insight_id"] is None
    assert body["generated_at"] is None
    assert body["provider"] is None and body["model"] is None
    assert body["prompt_version"] is None
    assert body["data_origin"] == "live"
    assert body["snapshot_id"] == world.snapshot.snapshot_id
    assert body["facts"]["engine_version"] == "1.0.0"
    assert body["facts"]["window_days"] == 90
    assert body["facts"]["overall"]["score"] == "83.32"
    assert [c["key"] for c in body["facts"]["components"]] == list(COMPONENT_KEYS)
    assert body["output"]["headline"]
    assert len(body["output"]["drivers"]) <= 3
    assert len(body["output"]["actions"]) <= 3
    # No prompt and no provider payload is on the wire. (`prompt_version` is part
    # of the contract; what must not appear is the prompt text itself.)
    for forbidden in (
        "prompt",
        "system_prompt",
        "user_prompt",
        "raw_response",
        "provider_response",
        "facts_json",
    ):
        assert forbidden not in body, forbidden


@pytest.mark.asyncio
async def test_a_demo_estate_is_reported_as_demo(db_session, async_client) -> None:
    world = await _seed_world(db_session, is_demo=True)

    response = await async_client.get(
        BRIEF_PATH,
        params={"estate_id": world.estate.estate_id},
        headers=_bearer(world.resident),
    )

    assert response.status_code == 200
    assert response.json()["data_origin"] == "demo"


@pytest.mark.asyncio
async def test_reading_an_estate_with_no_snapshot_is_404(db_session, async_client) -> None:
    estate = await _seed_estate(db_session, name="Unscored Estate")
    resident = await _seed_user(
        db_session, email="ai4_unscored@valora.test", role=UserRole.resident.value
    )
    await _seed_membership(
        db_session, user=resident, estate=estate, role=UserRole.resident.value
    )

    response = await async_client.get(
        BRIEF_PATH,
        params={"estate_id": estate.estate_id},
        headers=_bearer(resident),
    )

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "RESOURCE_NOT_FOUND"
    assert detail["request_id"] == response.headers["X-Request-ID"]
    assert detail["message"]


@pytest.mark.asyncio
async def test_a_non_member_cannot_read_the_brief(db_session, async_client) -> None:
    world = await _seed_world(db_session)

    response = await async_client.get(
        BRIEF_PATH,
        params={"estate_id": world.estate.estate_id},
        headers=_bearer(world.other_admin),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_an_admin_of_another_estate_cannot_read_or_generate(
    db_session, async_client
) -> None:
    world = await _seed_world(db_session)

    read = await async_client.get(
        BRIEF_PATH,
        params={"estate_id": world.other.estate_id},
        headers=_bearer(world.admin),
    )
    generate = await async_client.post(
        BRIEF_PATH,
        params={"estate_id": world.other.estate_id},
        headers=_bearer(world.admin),
    )

    assert read.status_code == 403
    assert generate.status_code == 403


@pytest.mark.asyncio
async def test_a_stored_insight_is_returned_over_http(db_session, async_client) -> None:
    world = await _seed_world(db_session)
    stored = await _insert_insight(
        db_session, estate=world.estate, snapshot=world.snapshot
    )

    response = await async_client.get(
        BRIEF_PATH,
        params={"estate_id": world.estate.estate_id},
        headers=_bearer(world.resident),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "ai"
    assert body["insight_id"] == stored.insight_id
    assert body["provider"] == "stub"
    assert body["model"] == "stub-model"
    assert body["prompt_version"] == PROMPT_VERSION
    assert body["generated_at"] is not None
    # The stored facts survived JSONB and came back as numbers.
    assert body["facts"]["overall"]["score"] == "83.32"
    assert body["output"]["headline"] == GROUNDED_OUTPUT["headline"]


# ------------------------------------------------------------------ generate


@pytest.mark.asyncio
async def test_a_resident_cannot_generate(db_session, async_client) -> None:
    world = await _seed_world(db_session)

    response = await async_client.post(
        BRIEF_PATH,
        params={"estate_id": world.estate.estate_id},
        headers=_bearer(world.resident),
    )

    assert response.status_code == 403
    assert response.json()["detail"]["message"]


@pytest.mark.asyncio
async def test_generate_with_ai_off_returns_the_template_and_stores_nothing(
    db_session, async_client
) -> None:
    world = await _seed_world(db_session)

    response = await async_client.post(
        BRIEF_PATH,
        params={"estate_id": world.estate.estate_id},
        headers=_bearer(world.admin),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "template"
    assert body["insight_id"] is None
    assert body["ai_unavailable_reason"] == "disabled"

    stored = await db_session.execute(select(AIInsight.insight_id))
    assert stored.scalars().all() == []

    # And the estate still reads a brief afterwards.
    again = await async_client.get(
        BRIEF_PATH,
        params={"estate_id": world.estate.estate_id},
        headers=_bearer(world.resident),
    )
    assert again.status_code == 200
    assert again.json()["source"] == "template"


@pytest.mark.asyncio
async def test_generate_with_the_fake_provider_stores_exactly_one_brief(
    db_session, async_client, ai_fake: None
) -> None:
    """The full path, hermetically: guard, ledger, validation, storage, idempotence."""
    world = await _seed_world(db_session)

    first = await async_client.post(
        BRIEF_PATH,
        params={"estate_id": world.estate.estate_id},
        headers=_bearer(world.admin),
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["source"] == "ai"
    assert body["insight_id"]
    assert body["ai_unavailable_reason"] is None
    assert body["provider"] == "fake"
    assert body["prompt_version"] == PROMPT_VERSION
    assert body["generated_at"] is not None
    assert body["data_origin"] == "live"

    # The stored facts are the FACTS contract, and they match the snapshot.
    stored = await db_session.execute(
        select(AIInsight).where(AIInsight.insight_id == body["insight_id"])
    )
    row = stored.scalar_one()
    assert row.snapshot_id == world.snapshot.snapshot_id
    assert row.kind == "health_brief"
    assert row.data_origin == "live"
    assert BriefFacts.model_validate(row.facts).overall.score == Decimal("83.32")

    # A second ask returns the same brief: one row, and one provider attempt.
    second = await async_client.post(
        BRIEF_PATH,
        params={"estate_id": world.estate.estate_id},
        headers=_bearer(world.admin),
    )
    assert second.status_code == 200
    assert second.json()["insight_id"] == body["insight_id"]

    rows = await db_session.execute(select(AIInsight.insight_id))
    assert len(rows.scalars().all()) == 1
    ledger = await db_session.execute(
        select(AICallEvent.feature, AICallEvent.status).where(
            AICallEvent.estate_id == world.estate.estate_id
        )
    )
    assert ledger.fetchall() == [("insights", "ok")]


@pytest.mark.asyncio
async def test_a_member_reads_a_stored_brief_without_another_provider_attempt(
    db_session, async_client, ai_fake: None
) -> None:
    world = await _seed_world(db_session)
    await async_client.post(
        BRIEF_PATH,
        params={"estate_id": world.estate.estate_id},
        headers=_bearer(world.admin),
    )

    read = await async_client.get(
        BRIEF_PATH,
        params={"estate_id": world.estate.estate_id},
        headers=_bearer(world.resident),
    )

    assert read.status_code == 200
    assert read.json()["source"] == "ai"
    ledger = await db_session.execute(
        select(AICallEvent.event_id).where(
            AICallEvent.estate_id == world.estate.estate_id
        )
    )
    assert len(ledger.scalars().all()) == 1


@pytest.mark.asyncio
async def test_generating_for_an_estate_without_a_snapshot_is_404(
    db_session, async_client
) -> None:
    estate = await _seed_estate(db_session, name="No Snapshot Estate")
    admin = await _seed_user(
        db_session, email="ai4_nosnap_admin@valora.test", role=UserRole.hoa_admin.value
    )
    await _seed_membership(
        db_session, user=admin, estate=estate, role=UserRole.hoa_admin.value
    )

    response = await async_client.post(
        BRIEF_PATH,
        params={"estate_id": estate.estate_id},
        headers=_bearer(admin),
    )

    assert response.status_code == 404


# ------------------------------------------------------------------ feedback


@pytest.mark.asyncio
async def test_feedback_is_recorded_once_per_user(db_session, async_client) -> None:
    world = await _seed_world(db_session)
    stored = await _insert_insight(
        db_session, estate=world.estate, snapshot=world.snapshot
    )

    first = await async_client.post(
        FEEDBACK_PATH.format(insight_id=stored.insight_id),
        params={"estate_id": world.estate.estate_id},
        json={"helpful": True, "comment": "Clear and useful."},
        headers=_bearer(world.resident),
    )
    repeat = await async_client.post(
        FEEDBACK_PATH.format(insight_id=stored.insight_id),
        params={"estate_id": world.estate.estate_id},
        json={"helpful": False},
        headers=_bearer(world.resident),
    )

    assert first.status_code == 200, first.text
    assert first.json()["helpful"] is True
    assert first.json()["comment"] == "Clear and useful."
    assert first.json()["id"]
    assert repeat.status_code == 409

    rows = await db_session.execute(select(AIInsightFeedback.feedback_id))
    assert len(rows.scalars().all()) == 1


@pytest.mark.asyncio
async def test_feedback_on_another_estates_insight_is_404(db_session, async_client) -> None:
    world = await _seed_world(db_session)
    stored = await _insert_insight(
        db_session, estate=world.estate, snapshot=world.snapshot
    )

    response = await async_client.post(
        FEEDBACK_PATH.format(insight_id=stored.insight_id),
        params={"estate_id": world.other.estate_id},
        json={"helpful": True},
        headers=_bearer(world.other_admin),
    )

    assert response.status_code == 403 or response.status_code == 404
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_a_resident_may_leave_feedback_but_a_non_member_may_not(
    db_session, async_client
) -> None:
    world = await _seed_world(db_session)
    stored = await _insert_insight(
        db_session, estate=world.estate, snapshot=world.snapshot
    )

    non_member = await async_client.post(
        FEEDBACK_PATH.format(insight_id=stored.insight_id),
        params={"estate_id": world.estate.estate_id},
        json={"helpful": True},
        headers=_bearer(world.other_admin),
    )
    member = await async_client.post(
        FEEDBACK_PATH.format(insight_id=stored.insight_id),
        params={"estate_id": world.estate.estate_id},
        json={"helpful": False, "comment": "Not enough detail."},
        headers=_bearer(world.resident),
    )

    assert non_member.status_code == 403
    assert member.status_code == 200


@pytest.mark.asyncio
async def test_an_over_long_comment_is_refused_by_the_api(db_session, async_client) -> None:
    world = await _seed_world(db_session)
    stored = await _insert_insight(
        db_session, estate=world.estate, snapshot=world.snapshot
    )

    response = await async_client.post(
        FEEDBACK_PATH.format(insight_id=stored.insight_id),
        params={"estate_id": world.estate.estate_id},
        json={"helpful": True, "comment": "x" * 501},
        headers=_bearer(world.resident),
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"


# ----------------------------------------------------------- schema integrity


@pytest.mark.asyncio
async def test_the_migrated_schema_exposes_both_tables(db_session) -> None:
    """The harness applied the migration; this is the applied result, not the file."""
    result = await db_session.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name IN "
            "('ai_insights', 'ai_insight_feedback') ORDER BY table_name;"
        )
    )
    assert [row[0] for row in result.fetchall()] == ["ai_insight_feedback", "ai_insights"]

    constraints = await db_session.execute(
        text(
            "SELECT conname FROM pg_constraint WHERE conname IN ("
            "'uq_ai_insights_snapshot_kind_prompt_version',"
            "'ck_ai_insights_kind',"
            "'ck_ai_insights_data_origin',"
            "'ck_ai_insights_facts_object',"
            "'ck_ai_insights_output_object',"
            "'uq_ai_insight_feedback_insight_id_user_id',"
            "'ck_ai_insight_feedback_comment_length',"
            "'fk_ai_insights_snapshot_id_living_score_snapshots',"
            "'fk_ai_insight_feedback_insight_id_ai_insights'"
            ") ORDER BY conname;"
        )
    )
    found = {row[0] for row in constraints.fetchall()}
    assert len(found) == 9, found


@pytest.mark.asyncio
async def test_the_database_refuses_a_second_insight_for_the_same_snapshot(
    db_session,
) -> None:
    world = await _seed_world(db_session)
    await _insert_insight(db_session, estate=world.estate, snapshot=world.snapshot)

    duplicate = AIInsight(
        estate_id=world.estate.estate_id,
        snapshot_id=world.snapshot.snapshot_id,
        kind="health_brief",
        prompt_version=PROMPT_VERSION,
        provider="stub",
        model="stub-model",
        facts={},
        output=GROUNDED_OUTPUT,
        data_origin="live",
    )
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_the_database_refuses_a_comment_over_the_limit(db_session) -> None:
    world = await _seed_world(db_session)
    stored = await _insert_insight(
        db_session, estate=world.estate, snapshot=world.snapshot
    )

    db_session.add(
        AIInsightFeedback(
            insight_id=stored.insight_id,
            estate_id=world.estate.estate_id,
            user_id=world.resident.user_id,
            helpful=True,
            comment="x" * 501,
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_a_second_feedback_row_from_the_same_user_is_refused(db_session) -> None:
    world = await _seed_world(db_session)
    stored = await _insert_insight(
        db_session, estate=world.estate, snapshot=world.snapshot
    )

    for _ in range(2):
        db_session.add(
            AIInsightFeedback(
                insight_id=stored.insight_id,
                estate_id=world.estate.estate_id,
                user_id=world.resident.user_id,
                helpful=True,
                comment=None,
            )
        )
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
