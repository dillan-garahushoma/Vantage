"""HealthBriefService behaviour (BATCH AI-4).

No database and no network: the snapshot, insight, feedback, estate and
membership repositories are in-memory fakes, and the AI client is a recording
stub wrapped in the real `GatedLLMClient` + `GuardedLLMClient` guardrails.

Most of these tests are about the fallback: whatever the AI layer does, the
estate still gets the deterministic template with 200, and nothing half-written
is stored.

Written before the implementation, per the batch.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError

from app.analytics.ai.brief_facts import COMPONENT_KEYS, build_brief_facts
from app.analytics.ai.brief_output import PROMPT_VERSION
from app.analytics.services.health_brief_service import HealthBriefService
from app.common.enums import UserRole
from app.core.ai.client import DataClass, GatedLLMClient, LLMResult
from app.core.ai.errors import AIUnavailableError
from app.core.ai.guard import GuardedLLMClient
from app.core.config import Settings
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.identity.services.estate_authorization_service import EstateAuthorizationService

AS_OF = datetime(2026, 10, 11, 9, 0, tzinfo=timezone.utc)
ESTATE = 7
OTHER_ESTATE = 8

PERSONAL_MARKER = "Thandi van der Merwe at unit A-101 emailed residents@example.com about the burst pipe"

# A brief that is grounded: every number here is a fact of the snapshot below
# (83.32 overall, 60.00 for frequency, 90 window days, 25.00 for its weight).
GROUNDED_OUTPUT: dict[str, Any] = {
    "headline": "Living Score 83.32 out of 100",
    "summary": "Over 90 days the estate scored 83.32, with complaint frequency at 60.00.",
    "drivers": [
        {
            "component": "frequency",
            "direction": "declining",
            "statement": "Complaint frequency scored 60.00 and carries a weight of 25.00.",
        }
    ],
    "actions": [
        {"component": "frequency", "action": "Review repeat complaint sources."},
    ],
}

UNGROUNDED_OUTPUT: dict[str, Any] = {
    **GROUNDED_OUTPUT,
    "summary": "The estate scored 77.40, well above the regional average of 68.00.",
}


def make_settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "ENVIRONMENT": "test",
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/valora_test",
        "SECRET_KEY": "test-secret-not-for-production-0123456789",
        "AI_ENABLED": True,
        "AI_INSIGHTS_ENABLED": True,
        "AI_TRIAGE_ENABLED": False,
        "AI_PERSONAL_DATA_ALLOWED": False,
        "AI_PROVIDER": "fake",
        "AI_MODEL": "fake-model",
        "AI_MAX_INPUT_CHARS": 6000,
        "AI_DAILY_CALL_CAP_PER_ESTATE": 200,
    }
    base.update(overrides)
    return Settings(**base)


# --------------------------------------------------------------------- fakes


def make_snapshot(
    *,
    snapshot_id: int = 11,
    estate_id: int = ESTATE,
    as_of: datetime = AS_OF,
    status: str = "scored",
    overall_score: str | None = "83.32",
    measured_weight: str = "1.00",
    insufficient: tuple[str, ...] = (),
) -> SimpleNamespace:
    scores = {
        "resolution": "98.85",
        "frequency": "60.00",
        "security": "93.33",
        "satisfaction": "83.33",
        "infrastructure": "75.00",
    }
    raw_inputs = {
        "resolution": {"avg_resolution_days": "1.33", "resolved_complaints": 3},
        "frequency": {"complaints_created": 4, "unit_count": 2, "coverage_days": 90},
        "security": {"incidents": 1, "coverage_days": 90, "unit_count": 2},
        "satisfaction": {"avg_rating": "4.33", "rated_count": 3},
        "infrastructure": {"work_orders_in_window": 4, "work_orders_completed": 3},
    }
    weights = {
        "resolution": "0.30",
        "frequency": "0.25",
        "security": "0.20",
        "satisfaction": "0.15",
        "infrastructure": "0.10",
    }
    components = []
    for key in COMPONENT_KEYS:
        missing = key in insufficient
        components.append(
            {
                "key": key,
                "weight": weights[key],
                "status": "insufficient_data" if missing else "measured",
                "score": None if missing else scores[key],
                "raw_inputs": raw_inputs[key],
                "benchmark": "a benchmark",
                "contribution": "0.00" if missing else "10.00",
                "lost_points": "0.00" if missing else "1.00",
                "explanation": "the engine's own sentence",
                "recommendation": None if missing else "Review this component.",
            }
        )
    explanation = {
        "engine_version": "1.0.0",
        "status": status,
        "overall_score": overall_score,
        "measured_weight": measured_weight,
        "components": components,
        "drivers": components,
    }
    return SimpleNamespace(
        snapshot_id=snapshot_id,
        estate_id=estate_id,
        engine_version="1.0.0",
        as_of=as_of,
        window_start=as_of - timedelta(days=90),
        calculated_at=as_of + timedelta(minutes=1),
        status=status,
        overall_score=None if overall_score is None else Decimal(overall_score),
        measured_weight=Decimal(measured_weight),
        resolution_score=None if "resolution" in insufficient else Decimal("98.85"),
        frequency_score=None if "frequency" in insufficient else Decimal("60.00"),
        security_score=None if "security" in insufficient else Decimal("93.33"),
        satisfaction_score=None if "satisfaction" in insufficient else Decimal("83.33"),
        infrastructure_score=None if "infrastructure" in insufficient else Decimal("75.00"),
        inputs={},
        explanation=explanation,
    )


class FakeSnapshotRepo:
    def __init__(self, latest: Any = None, previous: dict[int, Any] | None = None) -> None:
        self._latest = latest
        self._previous = previous or {}
        self.asked: list[datetime] = []

    async def latest_for_estate(self, *, estate_id: int):
        if self._latest is None or self._latest.estate_id != estate_id:
            return None
        return self._latest

    async def latest_on_or_before(self, *, estate_id: int, as_of: datetime):
        self.asked.append(as_of)
        candidate = self._previous.get(int((self._latest.as_of - as_of).days))
        if candidate is None:
            return None
        return candidate


class FakeInsightRepo:
    def __init__(self, existing: Any = None, *, conflict: bool = False) -> None:
        self.existing = existing
        self.rows: list[Any] = []
        self.added: list[dict[str, Any]] = []
        self.conflict = conflict
        self.winner: Any = None

    async def get_for_snapshot(self, *, estate_id: int, snapshot_id: int, kind: str, prompt_version: str):
        # Deliberately does NOT filter by estate: the real estate scoping is proven
        # against the database, and here the service's own cross-tenant guard is
        # what is under test, so the fake hands back whatever it holds.
        if self.winner is not None:
            return self.winner
        row = self.existing
        if row is None:
            return None
        if (
            row.snapshot_id == snapshot_id
            and row.kind == kind
            and row.prompt_version == prompt_version
        ):
            return row
        return None

    async def get_by_id_in_estate(self, *, insight_id: int, estate_id: int):
        for row in [self.existing, *self.rows]:
            if row is not None and row.insight_id == insight_id and row.estate_id == estate_id:
                return row
        return None

    async def add(self, **fields: Any):
        self.added.append(fields)
        if self.conflict:
            # Another request committed the same (snapshot, kind, prompt_version)
            # between our read and our write.
            self.winner = make_insight(**{**fields, "insight_id": 55})
            raise IntegrityError("INSERT INTO ai_insights", {}, Exception("duplicate key"))
        row = make_insight(**fields)
        self.rows.append(row)
        return row


def make_insight(
    *,
    snapshot: Any = None,
    insight_id: int = 12,
    estate_id: int = ESTATE,
    snapshot_id: int = 11,
    kind: str = "health_brief",
    prompt_version: str = PROMPT_VERSION,
    provider: str = "stub",
    model: str = "stub-model",
    facts: Any = None,
    output: Any = None,
    data_origin: str = "live",
    created_at: datetime | None = AS_OF + timedelta(minutes=2),
    **extra: Any,
):
    """A stored brief row. Its facts are real, built the way the service stores them.

    A stored row always holds facts that validate, because the service only ever
    writes ``BriefFacts.model_dump(mode="json")``. A fixture with invented facts
    would test a state the database cannot be in.
    """
    if facts is None:
        facts = build_brief_facts(snapshot or make_snapshot()).model_dump(mode="json")
    return SimpleNamespace(
        insight_id=insight_id,
        estate_id=estate_id,
        snapshot_id=snapshot_id,
        kind=kind,
        prompt_version=prompt_version,
        provider=provider,
        model=model,
        facts=facts,
        output=output if output is not None else GROUNDED_OUTPUT,
        data_origin=data_origin,
        created_at=created_at,
    )


class FakeFeedbackRepo:
    def __init__(self, existing: Any = None) -> None:
        self.existing = existing
        self.rows: list[Any] = []
        self.added: list[dict[str, Any]] = []

    async def get_by_insight_and_user(self, *, insight_id: int, user_id: int):
        row = self.existing
        if row is None:
            return None
        if row.insight_id == insight_id and row.user_id == user_id:
            return row
        return None

    async def add(self, **fields: Any):
        self.added.append(fields)
        row = SimpleNamespace(feedback_id=31, created_at=AS_OF, **fields)
        self.rows.append(row)
        return row


class FakeEstateRepo:
    def __init__(self, is_demo: bool = False, exists: bool = True) -> None:
        self.is_demo = is_demo
        self.exists = exists

    async def get_by_id(self, estate_id: int):
        if not self.exists:
            return None
        return SimpleNamespace(estate_id=estate_id, is_demo=self.is_demo)


class FakeMembershipRepo:
    def __init__(self, memberships: list[Any]) -> None:
        self._memberships = memberships

    async def list_for_user_and_estate(self, *, user_id: int, estate_id: int):
        return [
            m for m in self._memberships if m.user_id == user_id and m.estate_id == estate_id
        ]

    async def get_for_user_and_estate(self, *, user_id: int, estate_id: int):
        matches = await self.list_for_user_and_estate(user_id=user_id, estate_id=estate_id)
        return matches[0] if matches else None


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def refresh(self, instance: Any) -> None:
        return None


class FakeLedger:
    def __init__(self, used: int = 0) -> None:
        self.rows: list[dict[str, Any]] = []
        self.used = used

    async def record(self, **fields: Any) -> None:
        self.rows.append(fields)

    async def count_since(self, *, estate_id: int, since, statuses) -> int:
        return self.used


_UNSET = object()


class RecordingClient:
    """Provider stub that records exactly what the service sent it."""

    provider = "stub"
    model = "stub-model"

    def __init__(self, parsed: Any = _UNSET, *, reason: str | None = None) -> None:
        self.calls = 0
        self._parsed = GROUNDED_OUTPUT if parsed is _UNSET else parsed
        self._reason = reason
        self.system: str | None = None
        self.user: str | None = None
        self.schema: Any = None
        self.data_class: Any = None
        self.feature: str | None = None

    async def generate_json(self, *, system, user, schema, data_class, feature) -> LLMResult:
        self.calls += 1
        self.system, self.user, self.schema = system, user, schema
        self.data_class, self.feature = data_class, feature
        if self._reason is not None:
            raise AIUnavailableError(self._reason)
        return LLMResult(
            parsed=self._parsed,
            provider=self.provider,
            model=self.model,
            latency_ms=5,
            input_chars=len(system) + len(user),
        )


def _membership(estate_id: int, role: str, user_id: int = 1):
    return SimpleNamespace(
        membership_id=estate_id * 100 + user_id,
        user_id=user_id,
        estate_id=estate_id,
        membership_role=role,
        property_id=None,
    )


def make_service(
    *,
    snapshot: Any = None,
    previous: dict[int, Any] | None = None,
    insight: Any = None,
    insight_conflict: bool = False,
    feedback: Any = None,
    memberships: list[Any] | None = None,
    client: RecordingClient | None = None,
    settings: Settings | None = None,
    ledger: FakeLedger | None = None,
    is_demo: bool = False,
    estate_exists: bool = True,
):
    cfg = settings or make_settings()
    provider = client or RecordingClient()
    auth = EstateAuthorizationService.__new__(EstateAuthorizationService)
    auth._memberships = FakeMembershipRepo(
        memberships
        if memberships is not None
        # One estate with an admin and a resident in it, which is what the reads
        # and the feedback paths need before anything else is under test.
        else [
            _membership(ESTATE, UserRole.hoa_admin.value),
            _membership(ESTATE, UserRole.resident.value, user_id=2),
        ]
    )

    service = HealthBriefService.__new__(HealthBriefService)
    service._db = FakeDb()
    service._settings = cfg
    service._snapshots = FakeSnapshotRepo(snapshot, previous)
    service._insights = FakeInsightRepo(insight, conflict=insight_conflict)
    service._feedback = FakeFeedbackRepo(feedback)
    service._estates = FakeEstateRepo(is_demo=is_demo, exists=estate_exists)
    service._authorization = auth
    service._llm = GuardedLLMClient(cfg, GatedLLMClient(cfg, provider), ledger or FakeLedger())
    return service, provider, cfg


ADMIN = SimpleNamespace(user_id=1, role=UserRole.hoa_admin.value)
RESIDENT = SimpleNamespace(user_id=2, role=UserRole.resident.value)


# ---------------------------------------------------------------- read: owner


@pytest.mark.asyncio
async def test_a_member_without_an_ai_insight_gets_the_template() -> None:
    service, provider, _ = make_service(snapshot=make_snapshot())

    response = await service.read(ESTATE, RESIDENT)

    assert provider.calls == 0
    assert response.source == "template"
    assert response.insight_id is None
    assert response.generated_at is None
    assert response.provider is None and response.model is None
    assert response.prompt_version is None
    assert response.snapshot_id == 11
    assert response.as_of == AS_OF
    assert response.data_origin == "live"
    assert service._insights.rows == []


@pytest.mark.asyncio
async def test_a_stored_ai_insight_is_returned_verbatim_and_never_regenerated() -> None:
    snapshot = make_snapshot()
    stored = make_insight(snapshot=snapshot, output=GROUNDED_OUTPUT)
    service, provider, _ = make_service(snapshot=snapshot, insight=stored)

    response = await service.read(ESTATE, RESIDENT)

    assert provider.calls == 0
    assert response.source == "ai"
    assert response.insight_id == 12
    assert response.generated_at == stored.created_at
    assert response.provider == "stub"
    assert response.model == "stub-model"
    assert response.prompt_version == PROMPT_VERSION
    assert response.output.headline == GROUNDED_OUTPUT["headline"]


@pytest.mark.asyncio
async def test_reading_a_demo_estate_reports_the_demo_origin() -> None:
    service, _, _ = make_service(snapshot=make_snapshot(), is_demo=True)

    response = await service.read(ESTATE, RESIDENT)

    assert response.data_origin == "demo"


@pytest.mark.asyncio
async def test_reading_an_estate_that_was_never_scored_is_404() -> None:
    service, provider, _ = make_service(snapshot=None)

    with pytest.raises(NotFoundException):
        await service.read(ESTATE, RESIDENT)

    assert provider.calls == 0


@pytest.mark.asyncio
async def test_a_non_member_cannot_read_the_brief() -> None:
    service, _, _ = make_service(snapshot=make_snapshot(), memberships=[])

    with pytest.raises(ForbiddenException):
        await service.read(ESTATE, RESIDENT)


@pytest.mark.asyncio
async def test_a_member_of_another_estate_cannot_read_this_brief() -> None:
    service, _, _ = make_service(
        snapshot=make_snapshot(),
        memberships=[_membership(OTHER_ESTATE, UserRole.resident.value, user_id=2)],
    )

    with pytest.raises(ForbiddenException):
        await service.read(ESTATE, RESIDENT)


# ------------------------------------------------------------ generate: owner


@pytest.mark.asyncio
async def test_an_admin_generates_persists_and_returns_the_ai_brief() -> None:
    service, provider, _ = make_service(snapshot=make_snapshot(), ledger=FakeLedger())

    response = await service.generate(ESTATE, ADMIN)

    assert provider.calls == 1
    assert provider.feature == "insights"
    assert provider.data_class == DataClass.aggregate
    assert response.source == "ai"
    assert response.insight_id == 12
    assert response.snapshot_id == 11
    assert response.output.headline == GROUNDED_OUTPUT["headline"]
    assert response.provider == "stub"
    assert response.model == "stub-model"
    assert response.prompt_version == PROMPT_VERSION
    assert response.data_origin == "live"
    assert len(service._insights.rows) == 1
    stored = service._insights.added[0]
    assert stored["estate_id"] == ESTATE
    assert stored["snapshot_id"] == 11
    assert stored["kind"] == "health_brief"
    assert stored["prompt_version"] == PROMPT_VERSION
    assert stored["data_origin"] == "live"
    assert stored["facts"]["overall"]["score"] == "83.32"
    assert stored["output"]["headline"] == GROUNDED_OUTPUT["headline"]
    assert service._db.commits == 1


@pytest.mark.asyncio
async def test_the_ledger_records_the_insights_feature() -> None:
    ledger = FakeLedger()
    service, _, _ = make_service(snapshot=make_snapshot(), ledger=ledger)

    await service.generate(ESTATE, ADMIN)

    assert len(ledger.rows) == 1
    assert ledger.rows[0]["feature"] == "insights"
    assert ledger.rows[0]["status"] == "ok"
    assert ledger.rows[0]["estate_id"] == ESTATE


@pytest.mark.asyncio
async def test_the_prompt_carries_facts_only_never_personal_data() -> None:
    service, provider, _ = make_service(snapshot=make_snapshot())

    await service.generate(ESTATE, ADMIN)

    prompt = provider.user or ""
    assert "83.32" in prompt
    for forbidden in ("Thandi", "@", "A-101", "burst pipe", "residents@example.com"):
        assert forbidden not in prompt, forbidden
    assert "untrusted" not in prompt.lower()


@pytest.mark.asyncio
async def test_a_second_generate_returns_the_stored_row_without_another_call() -> None:
    snapshot = make_snapshot()
    service, provider, _ = make_service(
        snapshot=snapshot, insight=make_insight(snapshot=snapshot)
    )

    response = await service.generate(ESTATE, ADMIN)

    assert provider.calls == 0
    assert response.source == "ai"
    assert response.insight_id == 12
    assert service._insights.added == []


@pytest.mark.asyncio
async def test_generate_needs_the_global_role_and_a_membership() -> None:
    resident_only, _, _ = make_service(
        snapshot=make_snapshot(),
        memberships=[_membership(ESTATE, UserRole.resident.value, user_id=2)],
    )
    with pytest.raises(ForbiddenException):
        await resident_only.generate(ESTATE, RESIDENT)

    admin_of_another, _, _ = make_service(
        snapshot=make_snapshot(),
        memberships=[_membership(OTHER_ESTATE, UserRole.hoa_admin.value)],
    )
    with pytest.raises(ForbiddenException):
        await admin_of_another.generate(ESTATE, ADMIN)


@pytest.mark.asyncio
async def test_generating_for_an_unscored_estate_is_404() -> None:
    service, provider, _ = make_service(snapshot=None)

    with pytest.raises(NotFoundException):
        await service.generate(ESTATE, ADMIN)

    assert provider.calls == 0


# ----------------------------------------------------- generate: fallback paths


@pytest.mark.asyncio
async def test_an_insufficient_snapshot_gets_the_template_with_no_ai_call() -> None:
    snapshot = make_snapshot(
        status="insufficient_data",
        overall_score=None,
        measured_weight="0.10",
        insufficient=("frequency", "security", "satisfaction", "infrastructure"),
    )
    service, provider, _ = make_service(snapshot=snapshot)

    response = await service.generate(ESTATE, ADMIN)

    assert provider.calls == 0
    assert response.source == "template"
    assert response.insight_id is None
    assert response.ai_unavailable_reason == "insufficient_data"
    assert service._insights.added == []
    assert service._db.commits == 0


@pytest.mark.asyncio
async def test_ai_disabled_falls_back_to_the_template_and_stores_nothing() -> None:
    service, provider, _ = make_service(
        snapshot=make_snapshot(), settings=make_settings(AI_ENABLED=False)
    )

    response = await service.generate(ESTATE, ADMIN)

    assert provider.calls == 0
    assert response.source == "template"
    assert response.ai_unavailable_reason == "disabled"
    assert service._insights.added == []
    assert service._db.commits == 1  # the audit row for the refusal


@pytest.mark.asyncio
async def test_the_feature_flag_alone_is_enough_to_fall_back() -> None:
    service, provider, _ = make_service(
        snapshot=make_snapshot(), settings=make_settings(AI_INSIGHTS_ENABLED=False)
    )

    response = await service.generate(ESTATE, ADMIN)

    assert provider.calls == 0
    assert response.ai_unavailable_reason == "disabled"


@pytest.mark.asyncio
async def test_a_provider_error_falls_back_to_the_template() -> None:
    client = RecordingClient(reason="provider_error")
    service, _, _ = make_service(snapshot=make_snapshot(), client=client)

    response = await service.generate(ESTATE, ADMIN)

    assert client.calls == 1
    assert response.source == "template"
    assert response.ai_unavailable_reason == "provider_error"
    assert service._insights.added == []
    assert service._db.commits == 1


@pytest.mark.asyncio
async def test_an_exhausted_budget_never_reaches_the_provider() -> None:
    client = RecordingClient()
    service, _, _ = make_service(
        snapshot=make_snapshot(),
        client=client,
        ledger=FakeLedger(used=200),
        settings=make_settings(AI_DAILY_CALL_CAP_PER_ESTATE=200),
    )

    response = await service.generate(ESTATE, ADMIN)

    assert client.calls == 0
    assert response.source == "template"
    assert response.ai_unavailable_reason == "budget"
    assert service._insights.added == []


@pytest.mark.asyncio
async def test_invalid_output_from_the_provider_falls_back_to_the_template() -> None:
    client = RecordingClient(parsed={"headline": 12, "summary": None})
    service, _, _ = make_service(snapshot=make_snapshot(), client=client)

    response = await service.generate(ESTATE, ADMIN)

    assert client.calls == 1
    assert response.source == "template"
    assert response.ai_unavailable_reason == "invalid_output"
    assert service._insights.added == []


@pytest.mark.asyncio
async def test_a_non_object_provider_response_falls_back_to_the_template() -> None:
    service, _, _ = make_service(
        snapshot=make_snapshot(), client=RecordingClient(parsed="not a brief")
    )

    response = await service.generate(ESTATE, ADMIN)

    assert response.source == "template"
    assert response.ai_unavailable_reason == "invalid_output"


@pytest.mark.asyncio
async def test_ungrounded_output_is_rejected_rather_than_stored() -> None:
    service, _, _ = make_service(
        snapshot=make_snapshot(), client=RecordingClient(parsed=UNGROUNDED_OUTPUT)
    )

    response = await service.generate(ESTATE, ADMIN)

    assert response.source == "template"
    assert response.ai_unavailable_reason == "ungrounded_output"
    assert service._insights.added == []


@pytest.mark.asyncio
async def test_the_fallback_template_never_quotes_the_provider_output() -> None:
    service, _, _ = make_service(
        snapshot=make_snapshot(), client=RecordingClient(parsed=UNGROUNDED_OUTPUT)
    )

    response = await service.generate(ESTATE, ADMIN)

    assert "regional average" not in response.output.summary
    assert "77.40" not in response.output.summary


@pytest.mark.asyncio
async def test_a_failed_attempt_does_not_stop_a_later_success() -> None:
    failing = RecordingClient(reason="timeout")
    service, _, cfg = make_service(snapshot=make_snapshot(), client=failing)

    first = await service.generate(ESTATE, ADMIN)
    assert first.source == "template"

    working = RecordingClient()
    service._llm = GuardedLLMClient(cfg, GatedLLMClient(cfg, working), FakeLedger())
    second = await service.generate(ESTATE, ADMIN)

    assert second.source == "ai"
    assert len(service._insights.rows) == 1


@pytest.mark.asyncio
async def test_a_concurrent_generate_returns_the_winner_and_stores_only_one_row() -> None:
    service, _, _ = make_service(snapshot=make_snapshot(), insight_conflict=True)

    response = await service.generate(ESTATE, ADMIN)

    assert response.source == "ai"
    assert response.insight_id == 55
    assert service._db.rollbacks == 1
    assert len(service._insights.rows) == 0  # the winner's row is the only one
    assert service._insights.winner is not None


@pytest.mark.asyncio
async def test_the_service_refuses_an_insight_from_a_different_estate() -> None:
    """The cross-tenant guard is an assertion, because it means a query bug."""
    snapshot = make_snapshot()
    foreign = make_insight(snapshot=snapshot, estate_id=OTHER_ESTATE)
    service, _, _ = make_service(snapshot=snapshot, insight=foreign)

    with pytest.raises(AssertionError):
        await service.generate(ESTATE, ADMIN)
    with pytest.raises(AssertionError):
        await service.read(ESTATE, RESIDENT)


# ----------------------------------------------------------------- feedback


@pytest.mark.asyncio
async def test_a_member_can_leave_feedback_once() -> None:
    snapshot = make_snapshot()
    service, _, _ = make_service(snapshot=snapshot, insight=make_insight(snapshot=snapshot))

    response = await service.feedback(
        12, ESTATE, RESIDENT, helpful=True, comment="Useful summary."
    )

    assert response.feedback_id == 31
    assert response.insight_id == 12
    assert response.helpful is True
    assert response.comment == "Useful summary."
    assert service._feedback.added[0]["estate_id"] == ESTATE
    assert service._feedback.added[0]["user_id"] == RESIDENT.user_id
    assert service._db.commits == 1


@pytest.mark.asyncio
async def test_feedback_stores_the_comment_locally_and_sends_nothing_to_the_provider() -> None:
    snapshot = make_snapshot()
    service, provider, _ = make_service(
        snapshot=snapshot, insight=make_insight(snapshot=snapshot)
    )

    await service.feedback(12, ESTATE, RESIDENT, helpful=False, comment=PERSONAL_MARKER)

    assert service._feedback.rows[0].comment == PERSONAL_MARKER
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_a_repeat_feedback_from_the_same_user_is_a_conflict() -> None:
    snapshot = make_snapshot()
    existing = SimpleNamespace(
        feedback_id=30, insight_id=12, estate_id=ESTATE, user_id=RESIDENT.user_id
    )
    service, _, _ = make_service(
        snapshot=snapshot,
        insight=make_insight(snapshot=snapshot),
        feedback=existing,
    )

    with pytest.raises(ConflictException):
        await service.feedback(12, ESTATE, RESIDENT, helpful=True)

    assert service._feedback.added == []


@pytest.mark.asyncio
async def test_feedback_on_another_estates_insight_is_404() -> None:
    snapshot = make_snapshot()
    service, _, _ = make_service(
        snapshot=snapshot, insight=make_insight(snapshot=snapshot, estate_id=OTHER_ESTATE)
    )

    with pytest.raises(NotFoundException):
        await service.feedback(12, ESTATE, RESIDENT, helpful=True)


@pytest.mark.asyncio
async def test_feedback_for_an_unknown_insight_is_404() -> None:
    service, _, _ = make_service(snapshot=make_snapshot(), insight=None)

    with pytest.raises(NotFoundException):
        await service.feedback(999, ESTATE, RESIDENT, helpful=True)


@pytest.mark.asyncio
async def test_a_non_member_cannot_leave_feedback() -> None:
    snapshot = make_snapshot()
    service, _, _ = make_service(
        snapshot=snapshot, insight=make_insight(snapshot=snapshot), memberships=[]
    )

    with pytest.raises(ForbiddenException):
        await service.feedback(12, ESTATE, RESIDENT, helpful=True)


# ------------------------------------------------------- facts pipeline shape


@pytest.mark.asyncio
async def test_generate_reads_the_previous_snapshots_for_the_two_lookbacks() -> None:
    snapshot = make_snapshot()
    older = make_snapshot(
        snapshot_id=9, as_of=AS_OF - timedelta(days=90), overall_score="80.00"
    )
    service, _, _ = make_service(snapshot=snapshot, previous={90: older})

    response = await service.generate(ESTATE, ADMIN)

    assert service._snapshots.asked == [AS_OF - timedelta(days=30), AS_OF - timedelta(days=90)]
    assert response.facts.overall.delta_90d == Decimal("3.32")
    assert response.facts.overall.delta_30d is None

    # And the deltas are what the provider was given.
    assert "3.32" in (service._llm.inner.inner.user or "")


@pytest.mark.asyncio
async def test_the_response_carries_the_facts_it_was_built_from() -> None:
    service, _, _ = make_service(snapshot=make_snapshot())

    response = await service.generate(ESTATE, ADMIN)

    assert response.facts.engine_version == "1.0.0"
    assert response.facts.window_days == 90
    assert response.facts.compared_days == (30, 90)
    assert response.facts.overall.score == Decimal("83.32")
    assert [component.key for component in response.facts.components] == list(COMPONENT_KEYS)
