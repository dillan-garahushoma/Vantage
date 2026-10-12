"""BATCH 7C — Living Score endpoints, CLI recalculation and documentation.

Layered like the earlier batches:

* **DTO and wiring tests** run everywhere, with no database. They build a stored
  snapshot object from the engine's own JSON shape, so the DTO contract is tested
  against what 7B actually persists rather than against a hand-written fixture.
* **HTTP, CLI and isolation tests** (`@pytest.mark.integration`) need
  `TEST_DATABASE_URL` and auto-skip without it. Those are the only place a
  cross-estate claim is made.

Written before the implementation, per the batch.
"""
from __future__ import annotations

import inspect
import json
import os
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.analytics.engine import (
    COMPONENT_KEYS,
    COMPONENT_LABELS,
    ENGINE_VERSION,
    EstateScoreInputs,
    calculate_living_score,
)
from app.analytics.models.living_score_snapshot import LivingScoreSnapshot
from app.analytics.services.estate_living_score_service import (
    LivingScoreService,
    _inputs_to_json,
    _result_to_json,
)
from app.common.enums import UserRole
from app.core.security import create_access_token

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent

API_PREFIX = "/api/v1/analytics/living-score"
LATEST_PATH = API_PREFIX
RECALC_PATH = f"{API_PREFIX}/recalculate"
HISTORY_PATH = f"{API_PREFIX}/history"

ESTATE = 7
OTHER_ESTATE = 8
AS_OF = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
CALCULATED_AT = datetime(2026, 10, 10, 12, 0, 30, tzinfo=timezone.utc)

COMPONENT_DTO_FIELDS = {
    "key",
    "label",
    "weight",
    "status",
    "score",
    "inputs",
    "benchmark",
    "contribution",
    "lost_points",
    "explanation",
    "recommendation",
}

#: Text that must never appear in a score response: a complaint description and the
#: personal identifiers the fixtures use.
FORBIDDEN_IN_RESPONSE = ("DISTINCTIVE-COMPLAINT-TEXT-7C", "@valora.test", "password")


# --------------------------------------------------------------------------- #
# Building a stored snapshot the way 7B persists one (no database needed)
# --------------------------------------------------------------------------- #
def _inputs(**overrides) -> EstateScoreInputs:
    payload = {
        "as_of": AS_OF,
        "coverage_days": 90,
        "unit_count": 50,
        "complaints_created": 20,
        "resolved_complaints": 5,
        "avg_resolution_days": Decimal("6"),
        "work_orders_in_window": 8,
        "work_orders_completed": 6,
        "rated_count": 10,
        "avg_rating": Decimal("4.5"),
        "provider_rating_count": 5,
        "avg_provider_rating": Decimal("4"),
        "incidents": 3,
    }
    payload.update(overrides)
    return EstateScoreInputs(**payload)


def _sparse_inputs() -> EstateScoreInputs:
    """Too little evidence to score: 0.45 of the weight (7A decision D2/D3)."""
    return _inputs(
        coverage_days=10,
        unit_count=5,
        complaints_created=4,
        resolved_complaints=3,
        avg_resolution_days=Decimal("1"),
        work_orders_in_window=0,
        work_orders_completed=0,
        rated_count=3,
        avg_rating=Decimal("5"),
        provider_rating_count=0,
        avg_provider_rating=None,
        incidents=2,
    )


def _stored_snapshot(*, inputs: EstateScoreInputs | None = None, **overrides):
    """An unpersisted snapshot carrying exactly the JSON 7B stores."""
    engine_inputs = inputs or _inputs()
    result = calculate_living_score(engine_inputs)
    scores = {component.key: component.score for component in result.components}
    payload = {
        "snapshot_id": 11,
        "estate_id": ESTATE,
        "engine_version": result.engine_version,
        "as_of": engine_inputs.as_of,
        "window_start": result.window_start,
        "calculated_at": CALCULATED_AT,
        "calculated_by": 22,
        "status": result.status,
        "overall_score": result.overall_score,
        "measured_weight": result.measured_weight,
        "resolution_score": scores["resolution"],
        "frequency_score": scores["frequency"],
        "security_score": scores["security"],
        "satisfaction_score": scores["satisfaction"],
        "infrastructure_score": scores["infrastructure"],
        "inputs": _inputs_to_json(engine_inputs),
        "explanation": _result_to_json(result),
    }
    payload.update(overrides)
    return LivingScoreSnapshot(**payload)


# --------------------------------------------------------------------------- #
# 1. DTO contract
# --------------------------------------------------------------------------- #
def test_the_snapshot_response_exposes_the_whole_contract() -> None:
    from app.analytics.schemas.living_score_snapshot import LivingScoreSnapshotResponse

    payload = LivingScoreSnapshotResponse.from_stored_snapshot(
        _stored_snapshot(), is_demo=False
    ).model_dump(by_alias=True)

    assert set(payload) == {
        "id",
        "estate_id",
        "engine_version",
        "as_of",
        "window_start",
        "calculated_at",
        "status",
        "overall_score",
        "measured_weight",
        "is_demo",
        "components",
        "drivers",
    }
    assert payload["id"] == 11
    assert payload["estate_id"] == ESTATE
    assert payload["engine_version"] == ENGINE_VERSION
    assert payload["status"] == "scored"
    assert payload["measured_weight"] == Decimal("1.00")
    assert payload["is_demo"] is False
    assert len(payload["components"]) == 5
    assert payload["drivers"]


def test_every_component_carries_the_documented_fields() -> None:
    from app.analytics.schemas.living_score_snapshot import LivingScoreSnapshotResponse

    response = LivingScoreSnapshotResponse.from_stored_snapshot(
        _stored_snapshot(), is_demo=False
    )

    assert [component.key for component in response.components] == list(COMPONENT_KEYS)
    for component in response.components:
        assert set(component.model_dump(by_alias=True)) == COMPONENT_DTO_FIELDS
        assert component.label == COMPONENT_LABELS[component.key]
        assert component.status == "measured"
        assert component.benchmark
        assert component.explanation


def test_component_labels_are_the_engine_labels_for_every_key() -> None:
    from app.analytics.schemas.living_score_snapshot import LivingScoreSnapshotResponse

    response = LivingScoreSnapshotResponse.from_stored_snapshot(
        _stored_snapshot(), is_demo=False
    )

    labels = {component.key: component.label for component in response.components}
    assert labels == {
        "resolution": "Resolution speed",
        "frequency": "Complaint frequency",
        "security": "Security",
        "satisfaction": "Resident satisfaction",
        "infrastructure": "Maintenance completion",
    }


def test_the_scores_are_exact_decimals_not_floats() -> None:
    """A score is compared and stored; serialising it as a float would lose that."""
    from app.analytics.schemas.living_score_snapshot import LivingScoreSnapshotResponse

    response = LivingScoreSnapshotResponse.from_stored_snapshot(
        _stored_snapshot(), is_demo=False
    )

    assert response.overall_score == Decimal("84.45")
    assert isinstance(response.overall_score, Decimal)
    for component in response.components:
        assert isinstance(component.score, Decimal)
        assert isinstance(component.weight, Decimal)
        assert isinstance(component.contribution, Decimal)
        assert isinstance(component.lost_points, Decimal)
    assert response.components[0].score == Decimal("82.76")
    assert response.components[0].weight == Decimal("0.30")


def test_the_drivers_are_the_engine_order_and_are_components() -> None:
    from app.analytics.schemas.living_score_snapshot import LivingScoreSnapshotResponse

    response = LivingScoreSnapshotResponse.from_stored_snapshot(
        _stored_snapshot(), is_demo=False
    )

    assert [driver.key for driver in response.drivers] == [
        "resolution",
        "security",
        "infrastructure",
        "frequency",
        "satisfaction",
    ]
    for driver in response.drivers:
        assert set(driver.model_dump(by_alias=True)) == COMPONENT_DTO_FIELDS


def test_an_insufficient_snapshot_keeps_its_nulls() -> None:
    from app.analytics.schemas.living_score_snapshot import LivingScoreSnapshotResponse

    response = LivingScoreSnapshotResponse.from_stored_snapshot(
        _stored_snapshot(inputs=_sparse_inputs()), is_demo=True
    )

    assert response.status == "insufficient_data"
    assert response.overall_score is None
    assert response.is_demo is True
    scores = {component.key: component.score for component in response.components}
    assert scores["resolution"] == Decimal("100.00")
    # NULL, never a fabricated zero, for the components with no evidence.
    assert scores["frequency"] is None
    assert scores["security"] is None
    assert scores["infrastructure"] is None


def test_the_history_row_is_a_summary_and_carries_no_components() -> None:
    from app.analytics.schemas.living_score_snapshot import LivingScoreHistoryRow

    row = LivingScoreHistoryRow.from_stored_snapshot(_stored_snapshot())

    assert set(row.model_dump(by_alias=True)) == {
        "id",
        "as_of",
        "window_start",
        "status",
        "overall_score",
        "measured_weight",
        "engine_version",
    }
    assert row.snapshot_id == 11
    assert row.overall_score == Decimal("84.45")


def test_the_history_response_exposes_count_page_and_page_size() -> None:
    from app.analytics.schemas.living_score_snapshot import LivingScoreHistoryResponse
    from app.analytics.services.estate_living_score_service import SnapshotHistory

    history = SnapshotHistory(
        items=[_stored_snapshot(), _stored_snapshot(snapshot_id=10)],
        total=2,
        page=1,
        size=2,
    )
    response = LivingScoreHistoryResponse.from_history(history)

    assert set(response.model_dump(by_alias=True)) == {"count", "page", "page_size", "snapshots"}
    assert response.count == 2
    assert response.page == 1
    assert response.page_size == 2
    assert [row.snapshot_id for row in response.snapshots] == [11, 10]


def test_the_response_never_recomputes_from_the_engine() -> None:
    """The DTO is a projection of the stored row, so a stored value is returned as is."""
    from app.analytics.schemas.living_score_snapshot import LivingScoreSnapshotResponse

    stored = _stored_snapshot(overall_score=Decimal("12.34"), status="scored")
    response = LivingScoreSnapshotResponse.from_stored_snapshot(stored, is_demo=False)

    assert response.overall_score == Decimal("12.34")

    source = inspect.getsource(LivingScoreSnapshotResponse.from_stored_snapshot)
    assert "calculate_living_score" not in source
    assert "gather" not in source


def test_the_dto_never_exposes_orm_internals() -> None:
    from app.analytics.schemas.living_score_snapshot import (
        LivingScoreHistoryRow,
        LivingScoreSnapshotResponse,
    )

    forbidden = {"calculated_by", "inputs", "explanation", "_sa_instance_state"}
    snapshot_dump = set(
        LivingScoreSnapshotResponse.from_stored_snapshot(_stored_snapshot(), is_demo=False)
        .model_dump(by_alias=True)
    )
    row_dump = set(LivingScoreHistoryRow.from_stored_snapshot(_stored_snapshot()).model_dump(by_alias=True))

    # `inputs`/`explanation` exist only per component, never as raw snapshot columns.
    assert snapshot_dump & forbidden == set()
    assert row_dump & forbidden == set()


# --------------------------------------------------------------------------- #
# Fakes for the service-level tests. Query shape and policy only - never isolation.
# --------------------------------------------------------------------------- #
class FakeDb:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeSnapshotRepo:
    def __init__(self, *, latest=None, items: list | None = None, total: int = 0) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.added: list[dict] = []
        self._latest = latest
        self._items = items or []
        self._total = total

    async def add(self, **kwargs):
        self.calls.append(("add", kwargs))
        self.added.append(kwargs)
        return SimpleNamespace(snapshot_id=len(self.added), **kwargs)

    async def latest_for_estate(self, **kwargs):
        self.calls.append(("latest_for_estate", kwargs))
        return self._latest

    async def history(self, **kwargs):
        self.calls.append(("history", kwargs))
        return list(self._items)

    async def count(self, **kwargs):
        self.calls.append(("count", kwargs))
        return self._total


class FakeInputsRepo:
    def __init__(self, inputs: EstateScoreInputs | None = None) -> None:
        self.gather_calls: list[dict] = []
        self._inputs = inputs or _inputs()

    async def gather(self, *, estate_id: int, as_of: datetime) -> EstateScoreInputs:
        self.gather_calls.append({"estate_id": estate_id, "as_of": as_of})
        return self._inputs


class FakeEstateRepo:
    def __init__(self, *, demo_estates: set[int] | None = None, known: set[int] | None = None) -> None:
        self.demo_estates = demo_estates or set()
        self.known = known if known is not None else {ESTATE, OTHER_ESTATE}
        self.list_calls: list[dict] = []

    async def get_by_id(self, estate_id: int):
        return SimpleNamespace(estate_id=estate_id, is_demo=estate_id in self.demo_estates)

    async def list_ids_for_scoring(self, *, estate_id=None, include_demo: bool = False):
        self.list_calls.append({"estate_id": estate_id, "include_demo": include_demo})
        candidates = sorted(self.known) if estate_id is None else [estate_id]
        return [
            candidate
            for candidate in candidates
            if include_demo or candidate not in self.demo_estates
        ]


class FakeMembershipRepo:
    def __init__(self, memberships: list) -> None:
        self.memberships = memberships

    async def list_for_user_and_estate(self, *, user_id: int, estate_id: int):
        return [m for m in self.memberships if m.user_id == user_id and m.estate_id == estate_id]

    async def get_for_user_and_estate(self, *, user_id: int, estate_id: int):
        matches = await self.list_for_user_and_estate(user_id=user_id, estate_id=estate_id)
        return matches[0] if matches else None


def _membership(user_id: int, estate_id: int, role: str, property_id: int | None = None):
    return SimpleNamespace(
        user_id=user_id, estate_id=estate_id, property_id=property_id, membership_role=role
    )


def _service(
    *,
    snapshots: FakeSnapshotRepo | None = None,
    inputs: FakeInputsRepo | None = None,
    estates: FakeEstateRepo | None = None,
    memberships: list | None = None,
    db: FakeDb | None = None,
) -> LivingScoreService:
    from app.identity.services.estate_authorization_service import EstateAuthorizationService

    authorization = EstateAuthorizationService.__new__(EstateAuthorizationService)
    authorization._memberships = FakeMembershipRepo(memberships or [])

    service = LivingScoreService.__new__(LivingScoreService)
    service._db = db or FakeDb()
    service._snapshots = snapshots or FakeSnapshotRepo()
    service._inputs = inputs or FakeInputsRepo()
    service._estates = estates or FakeEstateRepo()
    service._authorization = authorization
    return service


def _admin(estate_id: int = ESTATE, user_id: int = 22):
    return SimpleNamespace(user_id=user_id, role=UserRole.hoa_admin.value)


def _resident(user_id: int = 21):
    return SimpleNamespace(user_id=user_id, role=UserRole.resident.value)


# --------------------------------------------------------------------------- #
# 2. The service shapes the API needs (is_demo, and the CLI sweep)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_latest_view_returns_none_when_the_estate_was_never_scored() -> None:
    service = _service(
        snapshots=FakeSnapshotRepo(latest=None),
        memberships=[_membership(21, ESTATE, UserRole.resident.value, 1)],
    )

    assert await service.latest_view(estate_id=ESTATE, user=_resident()) is None


@pytest.mark.asyncio
async def test_latest_view_carries_the_snapshot_and_the_demo_flag() -> None:
    stored = _stored_snapshot()
    service = _service(
        snapshots=FakeSnapshotRepo(latest=stored),
        estates=FakeEstateRepo(demo_estates={ESTATE}),
        memberships=[_membership(21, ESTATE, UserRole.resident.value, 1)],
    )

    view = await service.latest_view(estate_id=ESTATE, user=_resident())

    assert view is not None
    assert view.snapshot is stored
    assert view.is_demo is True


@pytest.mark.asyncio
async def test_latest_view_still_requires_membership() -> None:
    from app.core.exceptions import ForbiddenException

    service = _service(
        snapshots=FakeSnapshotRepo(latest=_stored_snapshot()),
        memberships=[_membership(21, OTHER_ESTATE, UserRole.resident.value, 1)],
    )

    with pytest.raises(ForbiddenException):
        await service.latest_view(estate_id=ESTATE, user=_resident())


@pytest.mark.asyncio
async def test_latest_view_never_recalculates() -> None:
    inputs = FakeInputsRepo()
    snapshots = FakeSnapshotRepo(latest=_stored_snapshot())
    service = _service(
        snapshots=snapshots,
        inputs=inputs,
        memberships=[_membership(21, ESTATE, UserRole.resident.value, 1)],
    )

    await service.latest_view(estate_id=ESTATE, user=_resident())

    assert inputs.gather_calls == []
    assert [name for name, _ in snapshots.calls] == ["latest_for_estate"]


@pytest.mark.asyncio
async def test_recalculate_view_scores_once_and_reports_the_demo_flag() -> None:
    db = FakeDb()
    snapshots = FakeSnapshotRepo()
    service = _service(
        snapshots=snapshots,
        db=db,
        estates=FakeEstateRepo(demo_estates={ESTATE}),
        memberships=[_membership(22, ESTATE, UserRole.hoa_admin.value)],
    )

    view = await service.recalculate_view(estate_id=ESTATE, admin=_admin(), as_of=AS_OF)

    assert view.snapshot.estate_id == ESTATE
    assert view.snapshot.engine_version == ENGINE_VERSION
    assert view.is_demo is True
    assert [name for name, _ in snapshots.calls] == ["add"]
    assert db.commits == 1


@pytest.mark.asyncio
async def test_recalculate_estates_scores_real_estates_only_by_default() -> None:
    """The CLI path: no actor at all, demo estates excluded unless asked for."""
    estates = FakeEstateRepo(demo_estates={OTHER_ESTATE}, known={ESTATE, OTHER_ESTATE})
    service = _service(estates=estates)

    snapshots = await service.recalculate_estates()

    assert [snapshot.estate_id for snapshot in snapshots] == [ESTATE]
    assert estates.list_calls == [{"estate_id": None, "include_demo": False}]


@pytest.mark.asyncio
async def test_recalculate_estates_can_include_demo_estates() -> None:
    estates = FakeEstateRepo(demo_estates={OTHER_ESTATE}, known={ESTATE, OTHER_ESTATE})
    service = _service(estates=estates)

    snapshots = await service.recalculate_estates(include_demo=True)

    assert [snapshot.estate_id for snapshot in snapshots] == [ESTATE, OTHER_ESTATE]


@pytest.mark.asyncio
async def test_recalculate_estates_can_target_one_estate() -> None:
    estates = FakeEstateRepo(demo_estates=set(), known={ESTATE, OTHER_ESTATE})
    service = _service(estates=estates)

    snapshots = await service.recalculate_estates(estate_id=OTHER_ESTATE)

    assert [snapshot.estate_id for snapshot in snapshots] == [OTHER_ESTATE]
    assert estates.list_calls == [{"estate_id": OTHER_ESTATE, "include_demo": False}]

# --------------------------------------------------------------------------- #
# 3. HTTP. Real database, real authorization, real isolation.
# --------------------------------------------------------------------------- #
# The world is seeded here rather than through ``tests.factories`` for the same
# reason as in 7B: this batch must not depend on that helper's history.


def _bearer(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.user_id)})}"}


async def _seed_world(db):
    """Three estates: a scored real one, a second real one, and a demo one."""
    from app.community.models.complaint import Complaint
    from app.community.models.maintenance_work_order import MaintenanceworkOrder
    from app.community.models.security_incident import SecurityIncident
    from app.identity.models.estate_membership import EstateMembership
    from app.identity.models.user import User
    from app.property.models.estate import Estate
    from app.property.models.property import Property
    from app.providers.models.service_provider import ServiceProvider

    now = datetime.now(timezone.utc)
    started = now - timedelta(days=60)

    estate_real = Estate(
        name="7C Zambezi", suburb="Montana", city="Pretoria", province="Gauteng",
        created_at=started,
    )
    estate_b = Estate(
        name="7C Silver Lakes", suburb="Silver Lakes", city="Pretoria", province="Gauteng",
        created_at=started,
    )
    estate_demo = Estate(
        name="7C Demo Estate", suburb="Centurion", city="Pretoria", province="Gauteng",
        created_at=started, is_demo=True,
    )
    db.add_all([estate_real, estate_b, estate_demo])
    await db.commit()

    admin_real = User(email="7c_admin@valora.test", password_hash="x", full_name="Admin Real",
                      role=UserRole.hoa_admin.value)
    resident_real = User(email="7c_resident@valora.test", password_hash="x", full_name="Resident Real",
                         role=UserRole.resident.value)
    admin_b = User(email="7c_admin_b@valora.test", password_hash="x", full_name="Admin B",
                   role=UserRole.hoa_admin.value)
    demo_resident = User(email="7c_demo@valora.test", password_hash="x", full_name="Demo Resident",
                         role=UserRole.resident.value)
    provider_user = User(email="7c_provider@valora.test", password_hash="x", full_name="Pete",
                         role=UserRole.service_provider.value)
    db.add_all([admin_real, resident_real, admin_b, demo_resident, provider_user])
    await db.commit()

    p1 = Property(estate_id=estate_real.estate_id, unit_no="7C-01", complex_name="Zambezi",
                  street_address="1 Zambezi Drive", suburb="Montana")
    p2 = Property(estate_id=estate_real.estate_id, unit_no="7C-02", complex_name="Zambezi",
                  street_address="2 Zambezi Drive", suburb="Montana")
    p3 = Property(estate_id=estate_b.estate_id, unit_no="7C-11", complex_name="Silver",
                  street_address="11 Fairway Lane", suburb="Silver Lakes")
    p4 = Property(estate_id=estate_demo.estate_id, unit_no="7C-21", complex_name="Demo",
                  street_address="21 Demo Close", suburb="Centurion")
    db.add_all([p1, p2, p3, p4])
    await db.commit()

    provider = ServiceProvider(user_id=provider_user.user_id, full_name="Pete Plumbing",
                               trade="plumbing", phone="0821234567",
                               email="7c_pete@plumbing.test", avg_rating=Decimal("4.00"))
    db.add(provider)
    await db.commit()

    db.add_all([
        EstateMembership(user_id=admin_real.user_id, estate_id=estate_real.estate_id,
                         membership_role=UserRole.hoa_admin.value),
        EstateMembership(user_id=resident_real.user_id, estate_id=estate_real.estate_id,
                         property_id=p1.unit_id, membership_role=UserRole.resident.value),
        EstateMembership(user_id=admin_b.user_id, estate_id=estate_b.estate_id,
                         membership_role=UserRole.hoa_admin.value),
        EstateMembership(user_id=demo_resident.user_id, estate_id=estate_demo.estate_id,
                         property_id=p4.unit_id, membership_role=UserRole.resident.value),
    ])
    await db.commit()

    def complaint(unit_id, status, raised, resolved=None, description="A reported problem."):
        return Complaint(
            user_id=resident_real.user_id, estate_id=estate_real.estate_id, unit_id=unit_id,
            category="water", description=description, priority="normal", status=status,
            created_at=now - timedelta(days=raised),
            resolved_at=None if resolved is None else now - timedelta(days=resolved),
        )

    c1 = complaint(p1.unit_id, "resolved", 40, 39, "DISTINCTIVE-COMPLAINT-TEXT-7C")
    c2 = complaint(p1.unit_id, "resolved", 30, 28)
    c3 = complaint(p2.unit_id, "resolved", 20, 19)
    c4 = complaint(p2.unit_id, "in_progress", 10)
    db.add_all([c1, c2, c3, c4])
    await db.commit()

    def work_order(complaint_row, status, assigned, resolved=None, rating=None):
        return MaintenanceworkOrder(
            complaint_id=complaint_row.complaint_id, estate_id=estate_real.estate_id,
            provider_id=provider.provider_id, status=status,
            assigned_at=now - timedelta(days=assigned),
            resolved_at=None if resolved is None else now - timedelta(days=resolved),
            resident_rating=rating,
        )

    db.add_all([
        work_order(c1, "completed", 39, 38, 5),
        work_order(c2, "completed", 28, 27, 4),
        work_order(c3, "completed", 19, 18, 4),
        work_order(c4, "in_progress", 9),
    ])
    db.add(SecurityIncident(estate_id=estate_real.estate_id, category="theft", severity="high",
                            status="open", occurred_at=now - timedelta(days=5)))
    await db.commit()

    return SimpleNamespace(
        now=now,
        property_real=p1,
        estate_real=estate_real,
        estate_b=estate_b,
        estate_demo=estate_demo,
        admin_real=admin_real,
        resident_real=resident_real,
        admin_b=admin_b,
        demo_resident=demo_resident,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_member_can_read_the_latest_score(db_session, async_client) -> None:
    world = await _seed_world(db_session)
    service = LivingScoreService(db_session)
    stored = await service.calculate_and_snapshot(
        estate_id=world.estate_real.estate_id, actor=world.admin_real, as_of=world.now
    )

    response = await async_client.get(
        LATEST_PATH,
        params={"estate_id": world.estate_real.estate_id},
        headers=_bearer(world.resident_real),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == stored.snapshot_id
    assert body["estate_id"] == world.estate_real.estate_id
    assert body["engine_version"] == ENGINE_VERSION
    assert body["status"] == "scored"
    assert body["overall_score"] == str(stored.overall_score)
    assert body["measured_weight"] == "1.00"
    assert body["is_demo"] is False
    assert [component["key"] for component in body["components"]] == list(COMPONENT_KEYS)
    assert len(body["components"]) == 5
    # In this estate complaint frequency is the biggest drag (4 complaints over 2
    # units costs 10.00 of the score); resolution is near-perfect and costs ~0.34.
    assert body["drivers"][0]["key"] == "frequency"
    lost = [Decimal(component["lost_points"]) for component in body["drivers"]]
    assert lost == sorted(lost, reverse=True)
    for component in body["components"]:
        assert component["label"]
        assert component["benchmark"]
        assert isinstance(component["inputs"], dict)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_the_latest_route_is_404_when_the_estate_was_never_scored(
    db_session, async_client
) -> None:
    world = await _seed_world(db_session)

    response = await async_client.get(
        LATEST_PATH,
        params={"estate_id": world.estate_real.estate_id},
        headers=_bearer(world.resident_real),
    )

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "RESOURCE_NOT_FOUND"
    assert detail["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_resident_cannot_recalculate(db_session, async_client) -> None:
    world = await _seed_world(db_session)

    response = await async_client.post(
        RECALC_PATH,
        params={"estate_id": world.estate_real.estate_id},
        headers=_bearer(world.resident_real),
    )

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["request_id"] == response.headers["X-Request-ID"]
    assert detail["message"]

    # Nothing was written by the refused attempt.
    page = await LivingScoreService(db_session).history(
        estate_id=world.estate_real.estate_id, user=world.resident_real, page=1, size=20
    )
    assert page.total == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_an_admin_of_another_estate_cannot_read_or_recalculate(
    db_session, async_client
) -> None:
    world = await _seed_world(db_session)
    service = LivingScoreService(db_session)
    await service.calculate_and_snapshot(
        estate_id=world.estate_real.estate_id, actor=world.admin_real, as_of=world.now
    )
    headers = _bearer(world.admin_b)
    params = {"estate_id": world.estate_real.estate_id}

    read = await async_client.get(LATEST_PATH, params=params, headers=headers)
    recalc = await async_client.post(RECALC_PATH, params=params, headers=headers)
    history = await async_client.get(HISTORY_PATH, params=params, headers=headers)

    for response in (read, recalc, history):
        assert response.status_code == 403, response.text
        assert response.json()["detail"]["code"] == "FORBIDDEN"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_an_admin_recalculates_and_the_snapshot_is_appended(
    db_session, async_client
) -> None:
    world = await _seed_world(db_session)

    response = await async_client.post(
        RECALC_PATH,
        params={"estate_id": world.estate_real.estate_id},
        headers=_bearer(world.admin_real),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["engine_version"] == ENGINE_VERSION
    assert body["status"] == "scored"
    assert body["overall_score"] is not None
    assert body["id"] is not None
    assert len(body["components"]) == 5

    # A second calculation appends; it never rewrites the first.
    second = await async_client.post(
        RECALC_PATH,
        params={"estate_id": world.estate_real.estate_id},
        headers=_bearer(world.admin_real),
    )
    assert second.status_code == 201
    assert second.json()["id"] != body["id"]

    page = await LivingScoreService(db_session).history(
        estate_id=world.estate_real.estate_id, user=world.resident_real, page=1, size=20
    )
    assert page.total == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_history_is_newest_first_and_paginates_with_bounds(
    db_session, async_client
) -> None:
    world = await _seed_world(db_session)
    service = LivingScoreService(db_session)
    older = await service.calculate_and_snapshot(
        estate_id=world.estate_real.estate_id, actor=world.admin_real,
        as_of=world.now - timedelta(days=30),
    )
    newer = await service.calculate_and_snapshot(
        estate_id=world.estate_real.estate_id, actor=world.admin_real, as_of=world.now
    )
    headers = _bearer(world.resident_real)

    page = await async_client.get(
        HISTORY_PATH,
        params={"estate_id": world.estate_real.estate_id, "page": 1, "page_size": 20},
        headers=headers,
    )
    assert page.status_code == 200, page.text
    body = page.json()
    assert set(body) == {"count", "page", "page_size", "snapshots"}
    assert body["count"] == 2
    assert [row["id"] for row in body["snapshots"]] == [newer.snapshot_id, older.snapshot_id]
    # Summary rows only: no component breakdown in history.
    assert set(body["snapshots"][0]) == {
        "id", "as_of", "window_start", "status", "overall_score", "measured_weight",
        "engine_version",
    }

    first = await async_client.get(
        HISTORY_PATH,
        params={"estate_id": world.estate_real.estate_id, "page": 1, "page_size": 1},
        headers=headers,
    )
    assert first.json()["count"] == 2
    assert [row["id"] for row in first.json()["snapshots"]] == [newer.snapshot_id]

    second = await async_client.get(
        HISTORY_PATH,
        params={"estate_id": world.estate_real.estate_id, "page": 2, "page_size": 1},
        headers=headers,
    )
    assert [row["id"] for row in second.json()["snapshots"]] == [older.snapshot_id]

    too_big = await async_client.get(
        HISTORY_PATH,
        params={"estate_id": world.estate_real.estate_id, "page_size": 101},
        headers=headers,
    )
    assert too_big.status_code == 422
    assert too_big.json()["detail"]["code"] == "VALIDATION_ERROR"

    zero_page = await async_client.get(
        HISTORY_PATH,
        params={"estate_id": world.estate_real.estate_id, "page": 0},
        headers=headers,
    )
    assert zero_page.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_stored_score_does_not_move_when_the_data_changes(
    db_session, async_client
) -> None:
    """Immutability through the API: new operations change nothing already stored."""
    from app.community.models.complaint import Complaint

    world = await _seed_world(db_session)
    service = LivingScoreService(db_session)
    stored = await service.calculate_and_snapshot(
        estate_id=world.estate_real.estate_id, actor=world.admin_real, as_of=world.now
    )
    headers = _bearer(world.resident_real)
    params = {"estate_id": world.estate_real.estate_id}

    before = (await async_client.get(LATEST_PATH, params=params, headers=headers)).json()

    # The estate's operations change after the calculation.
    db_session.add_all([
        Complaint(
            user_id=world.resident_real.user_id, estate_id=world.estate_real.estate_id,
            unit_id=world.property_real.unit_id,
            category="water", description="Later problem.", priority="normal",
            status="resolved", created_at=world.now - timedelta(days=2),
            resolved_at=world.now - timedelta(days=1),
        )
    ])
    await db_session.commit()

    after = (await async_client.get(LATEST_PATH, params=params, headers=headers)).json()
    history = (await async_client.get(HISTORY_PATH, params=params, headers=headers)).json()

    assert after == before
    assert after["id"] == stored.snapshot_id
    assert history["count"] == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_no_response_leaks_complaint_text_or_personal_data(
    db_session, async_client
) -> None:
    world = await _seed_world(db_session)
    await LivingScoreService(db_session).calculate_and_snapshot(
        estate_id=world.estate_real.estate_id, actor=world.admin_real, as_of=world.now
    )
    headers = _bearer(world.resident_real)
    params = {"estate_id": world.estate_real.estate_id}

    bodies = [
        (await async_client.get(LATEST_PATH, params=params, headers=headers)).text,
        (await async_client.get(HISTORY_PATH, params=params, headers=headers)).text,
    ]

    for body in bodies:
        for forbidden in FORBIDDEN_IN_RESPONSE:
            assert forbidden not in body, forbidden
        assert "user_id" not in body
        assert "description" not in body


@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_demo_estate_is_flagged_in_the_response(db_session, async_client) -> None:
    world = await _seed_world(db_session)
    # The CLI path (no actor) is the only way a demo estate is scored.
    await LivingScoreService(db_session).calculate_and_snapshot(
        estate_id=world.estate_demo.estate_id, actor=None, as_of=world.now
    )

    response = await async_client.get(
        LATEST_PATH,
        params={"estate_id": world.estate_demo.estate_id},
        headers=_bearer(world.demo_resident),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["is_demo"] is True
    # A brand-new estate is not silently "healthy": too little of it was measurable.
    assert body["status"] == "insufficient_data"
    assert body["overall_score"] is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_non_member_cannot_read_the_score(db_session, async_client) -> None:
    world = await _seed_world(db_session)
    await LivingScoreService(db_session).calculate_and_snapshot(
        estate_id=world.estate_real.estate_id, actor=world.admin_real, as_of=world.now
    )

    response = await async_client.get(
        LATEST_PATH,
        params={"estate_id": world.estate_real.estate_id},
        headers=_bearer(world.admin_b),
    )

    assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_the_routes_require_a_token(db_session, async_client) -> None:
    world = await _seed_world(db_session)

    response = await async_client.get(
        LATEST_PATH, params={"estate_id": world.estate_real.estate_id}
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHENTICATED"

# --------------------------------------------------------------------------- #
# 4. The CLI: the hook a scheduled job calls
# --------------------------------------------------------------------------- #
def _cli(argv: list[str]) -> None:
    import sys

    from app import cli

    original = sys.argv
    sys.argv = ["python -m app.cli", *argv]
    try:
        cli.main()
    finally:
        sys.argv = original


def test_the_cli_exposes_the_recalculation_command() -> None:
    from app import cli

    source = inspect.getsource(cli)
    assert "recalc-living-scores" in source
    assert "--estate-id" in source
    assert "--include-demo" in source


def test_the_cli_adds_no_queue_or_scheduler() -> None:
    """The daily cadence is Windows Task Scheduler's business, not the CLI's.

    Checked against the module's imports: prose may mention the scheduler that
    calls this command, but the command must not bundle one.
    """
    from app import cli

    imports = [
        line.strip().lower()
        for line in inspect.getsource(cli).splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for forbidden in (
        "apscheduler",
        "celery",
        "dramatiq",
        "rq",
        "sched",
        "crontab",
        "background",
    ):
        assert not any(forbidden in line for line in imports), forbidden


def test_the_cli_prints_one_line_per_estate_with_no_personal_data(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """The command's real interface: argv in, one line per estate out."""
    import app.analytics.services.estate_living_score_service as service_module

    scored = SimpleNamespace(
        estate_id=1, status="scored", overall_score=Decimal("84.45"), engine_version="1.0.0"
    )
    unscored = SimpleNamespace(
        estate_id=2, status="insufficient_data", overall_score=None, engine_version="1.0.0"
    )
    calls: list[dict] = []

    class RecordingService:
        def __init__(self, _session) -> None:
            pass

        async def recalculate_estates(self, *, estate_id=None, include_demo: bool = False):
            calls.append({"estate_id": estate_id, "include_demo": include_demo})
            return [scored, unscored]

    monkeypatch.setattr(service_module, "LivingScoreService", RecordingService)

    _cli(["recalc-living-scores"])

    lines = capsys.readouterr().out.strip().splitlines()
    assert lines == [
        "estate 1: status=scored score=84.45 engine=1.0.0",
        "estate 2: status=insufficient_data score=none engine=1.0.0",
    ]
    assert calls == [{"estate_id": None, "include_demo": False}]
    for line in lines:
        assert "@" not in line
        assert "password" not in line.lower()


def test_the_cli_passes_its_flags_through(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    import app.analytics.services.estate_living_score_service as service_module

    calls: list[dict] = []

    class RecordingService:
        def __init__(self, _session) -> None:
            pass

        async def recalculate_estates(self, *, estate_id=None, include_demo: bool = False):
            calls.append({"estate_id": estate_id, "include_demo": include_demo})
            return []

    monkeypatch.setattr(service_module, "LivingScoreService", RecordingService)

    _cli(["recalc-living-scores", "--estate-id", "9", "--include-demo"])

    assert calls == [{"estate_id": 9, "include_demo": True}]
    assert capsys.readouterr().out == ""


@pytest.mark.integration
@pytest.mark.asyncio
async def test_the_cli_sweep_scores_real_estates_and_skips_demo_ones(db_session) -> None:
    world = await _seed_world(db_session)
    service = LivingScoreService(db_session)

    scored = await service.recalculate_estates()

    ids = sorted(snapshot.estate_id for snapshot in scored)
    assert ids == sorted([world.estate_real.estate_id, world.estate_b.estate_id])
    assert world.estate_demo.estate_id not in ids

    page = await service.history(
        estate_id=world.estate_demo.estate_id, user=world.demo_resident, page=1, size=20
    )
    assert page.total == 0, "a demo estate must not be scored by the default sweep"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_the_cli_sweep_can_include_demo_estates(db_session) -> None:
    world = await _seed_world(db_session)
    service = LivingScoreService(db_session)

    scored = await service.recalculate_estates(include_demo=True)

    ids = sorted(snapshot.estate_id for snapshot in scored)
    assert ids == sorted(
        [world.estate_real.estate_id, world.estate_b.estate_id, world.estate_demo.estate_id]
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_the_cli_sweep_can_target_a_single_estate(db_session) -> None:
    world = await _seed_world(db_session)
    service = LivingScoreService(db_session)

    scored = await service.recalculate_estates(estate_id=world.estate_b.estate_id)

    assert [snapshot.estate_id for snapshot in scored] == [world.estate_b.estate_id]
    untouched = await service.history(
        estate_id=world.estate_real.estate_id, user=world.resident_real, page=1, size=20
    )
    assert untouched.total == 0

# --------------------------------------------------------------------------- #
# 5. Wiring, contracts and documentation
# --------------------------------------------------------------------------- #
def _registered_paths() -> dict[str, set]:
    """The mounted contract, keyed by path.

    Read from the OpenAPI document rather than `app.routes`: this FastAPI keeps
    included routers wrapped until the schema is generated.
    """
    from app.main import app

    return {
        path: {method.upper() for method in operations}
        for path, operations in app.openapi()["paths"].items()
    }


def test_the_three_routes_are_registered_under_api_v1() -> None:
    paths = set(_registered_paths())

    assert LATEST_PATH in paths
    assert RECALC_PATH in paths
    assert HISTORY_PATH in paths
    for path in (LATEST_PATH, RECALC_PATH, HISTORY_PATH):
        assert path.startswith("/api/v1/")


def test_the_recalculation_route_is_a_post_and_the_reads_are_gets() -> None:
    methods = _registered_paths()

    assert "GET" in methods[LATEST_PATH] and "POST" not in methods[LATEST_PATH]
    assert "GET" in methods[HISTORY_PATH] and "POST" not in methods[HISTORY_PATH]
    assert "POST" in methods[RECALC_PATH] and "GET" not in methods[RECALC_PATH]


def test_the_openapi_document_exposes_the_new_paths_and_keeps_the_legacy_score() -> None:
    from app.main import app

    document = app.openapi()

    for path in (LATEST_PATH, RECALC_PATH, HISTORY_PATH):
        assert path in document["paths"], path
    # The estate score lives only under /analytics. Any other living-score path
    # in the contract is the deprecated per-property route, still where it was.
    others = [
        path
        for path in document["paths"]
        if "living-score" in path
        and path not in (LATEST_PATH, RECALC_PATH, HISTORY_PATH)
    ]
    assert all(path.startswith("/api/v1/properties/") for path in others), others


def test_the_router_leaks_no_orm_model_or_repository() -> None:
    """A router parses HTTP and calls a service; it never touches a row."""
    from app.analytics.api import living_score as router_module

    source = inspect.getsource(router_module)
    imports = [
        line.strip()
        for line in source.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]

    for forbidden in ("app.analytics.repositories", "app.analytics.models", "sqlalchemy.orm"):
        assert not any(forbidden in line for line in imports), forbidden
    assert "select(" not in source
    assert "LivingScoreService" in source


def test_the_router_does_not_rebuild_the_score_itself() -> None:
    """No scoring maths in the router: it asks the service and returns the row."""
    from app.analytics.api import living_score as router_module

    source = inspect.getsource(router_module)
    imports = [
        line.strip()
        for line in source.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]

    assert not any("app.analytics.engine" in line for line in imports)
    for forbidden in (r"\bcalculate_living_score\(", r"\bwindow_bounds\(", r"\bgather\("):
        assert not re.search(forbidden, source), forbidden


def test_the_legacy_property_score_is_left_alone() -> None:
    """The old per-property route keeps its own service and is not rewired."""
    legacy_service = (BACKEND_DIR / "app/analytics/services/living_score_service.py").read_text(
        encoding="utf-8"
    )
    legacy_repo = (BACKEND_DIR / "app/analytics/repositories/living_score_repository.py").read_text(
        encoding="utf-8"
    )

    for source in (legacy_service, legacy_repo):
        assert "LivingScoreSnapshot" not in source
        assert "estate_living_score_service" not in source
        assert "living_score_snapshots" not in source


def test_the_living_score_documentation_exists_and_states_the_rules() -> None:
    document = REPO_ROOT / "docs" / "LIVING_SCORE_V1.md"

    assert document.exists(), "docs/LIVING_SCORE_V1.md must exist"
    text = document.read_text(encoding="utf-8")
    for endpoint in (LATEST_PATH, RECALC_PATH, HISTORY_PATH):
        assert endpoint in text, endpoint
    for decision in ("D1", "D2", "D3", "D4", "D5", "D6"):
        assert decision in text, decision
    assert "insufficient_data" in text
    assert "engine version" in text.lower()
    assert "new engine version" in text.lower()
    for weight in ("0.30", "0.25", "0.20", "0.15", "0.10"):
        assert weight in text, weight


def test_the_score_documentation_names_the_authority() -> None:
    text = (REPO_ROOT / "docs" / "LIVING_SCORE_V1.md").read_text(encoding="utf-8")

    assert "ADR-005" in text
    assert "LegacyPropertyScore" in text or "legacy" in text.lower()


def test_the_task_list_marks_6_and_7_only_with_evidence() -> None:
    """Ticked criteria must point at something a reader can run."""
    text = (REPO_ROOT / "tasks" / "todo.md").read_text(encoding="utf-8")

    task_7 = text.split("### Task 7:")[1].split("### Checkpoint")[0]
    assert task_7.count("[x]") == 3, task_7
    assert "test_living_score" in task_7
    task_6 = text.split("### Task 6:")[1].split("### Task 7:")[0]
    assert task_6.count("[x]") == 3, task_6
