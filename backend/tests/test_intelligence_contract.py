"""Tests for the VALORA Intelligence schemas, domain logic, and API contract."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.analytics.schemas.intelligence import (
    AskValoraRequest,
    AskValoraResponse,
    EstateIntelligenceResponse,
    OperationalSignalCounts,
    PriorityRecommendation,
    ProviderIntelligenceView,
    ProviderWorkOrderSummary,
    RecommendationEvidence,
    ResidentIntelligenceView,
    ResidentUnitIssue,
    WeeklyBriefing,
    WorkOrderDefaults,
)
from app.analytics.services.intelligence_service import IntelligenceService, _briefing
from app.main import app


def test_grounded_briefing_contains_only_measured_counts():
    facts = {'counts': {'open_complaints': 101, 'work_orders_in_flight': 2, 'unresolved_incidents': 1}}
    briefing = _briefing('Fictional Musgrave', facts)
    assert briefing.signals_reviewed == 104
    assert briefing.avoidable_zar is None
    assert '101 open complaints' in briefing.body


def test_weekly_briefing_schema_valid() -> None:
    briefing = WeeklyBriefing(
        headline="Three issues deserve attention this week.",
        body="Acting on two of them could prevent an estimated R86,000 in reactive maintenance.",
        window_label="Rolling 7 days",
        signals_reviewed=1284,
        sources=9,
        avoidable_zar=86000.0,
    )
    dump = briefing.model_dump(by_alias=True)
    assert dump["headline"] == "Three issues deserve attention this week."
    assert dump["windowLabel"] == "Rolling 7 days"
    assert dump["signalsReviewed"] == 1284
    assert dump["avoidableZar"] == 86000.0


def test_ask_valora_request_validation() -> None:
    # Valid
    req = AskValoraRequest(question="Why did our score drop?", estate_id=1)
    assert req.question == "Why did our score drop?"
    assert req.estate_id == 1

    # Question too short
    with pytest.raises(ValidationError):
        AskValoraRequest(question="ab", estate_id=1)

    # Estate ID invalid
    with pytest.raises(ValidationError):
        AskValoraRequest(question="Why did our score drop?", estate_id=0)


def test_openapi_routes_registered() -> None:
    openapi = app.openapi()
    paths = openapi.get("paths", {})

    assert "/api/v1/analytics/intelligence" in paths
    assert "get" in paths["/api/v1/analytics/intelligence"]

    assert "/api/v1/analytics/intelligence/ask" in paths
    assert "post" in paths["/api/v1/analytics/intelligence/ask"]

    assert "/api/v1/analytics/intelligence/ask/stream" in paths
    assert "post" in paths["/api/v1/analytics/intelligence/ask/stream"]

    assert "/api/v1/analytics/intelligence/signals" in paths
    assert "get" in paths["/api/v1/analytics/intelligence/signals"]

    assert "/api/v1/analytics/intelligence/briefing" in paths
    assert "post" in paths["/api/v1/analytics/intelligence/briefing"]


def test_estate_signal_items_mapping() -> None:
    from app.analytics.models.living_score_snapshot import LivingScoreSnapshot
    from app.community.models.security_incident import SecurityIncident
    from app.analytics.schemas.intelligence import EstateSignalItem

    # Mock snapshot
    snap = LivingScoreSnapshot(
        snapshot_id=1,
        estate_id=1,
        engine_version="1.0.0",
        as_of=datetime.now(timezone.utc),
        window_start=datetime.now(timezone.utc),
        status="published",
        overall_score=85.5,
        measured_weight=1.0,
        resolution_score=90.0,
        security_score=80.0,
        infrastructure_score=85.0,
        inputs={},
        explanation={},
    )

    item = EstateSignalItem(
        type="living_score",
        id=snap.snapshot_id,
        title=f"Living Score Snapshot: {snap.overall_score}/100",
        status="published",
        date=snap.as_of.isoformat() if snap.as_of else "",
        detail=f"Resolution: {snap.resolution_score}, Security: {snap.security_score}, Maintenance: {snap.infrastructure_score}",
    )
    assert item.title == "Living Score Snapshot: 85.5/100"
    assert "Resolution: 90.0" in item.detail

    # Mock incident
    inc = SecurityIncident(
        incident_id=10,
        estate_id=1,
        category="theft",
        severity="medium",
        status="open",
        occurred_at=datetime.now(timezone.utc),
        resolution_notes="Patrol dispatched",
    )
    inc_item = EstateSignalItem(
        type="incident",
        id=inc.incident_id,
        title=f"Security Incident: {inc.category} ({inc.severity})",
        status=inc.status or "open",
        date=inc.created_at.isoformat() if inc.created_at else "",
        detail=inc.resolution_notes or "",
    )
    assert inc_item.detail == "Patrol dispatched"


@pytest.mark.asyncio
async def test_resident_receives_resident_view_without_recommendations():
    service = IntelligenceService(AsyncMock())
    service._auth = SimpleNamespace(
        resolve_access=AsyncMock(
            return_value=SimpleNamespace(
                is_estate_admin=False,
                is_estate_provider=False,
                membership_roles=frozenset({"resident"}),
            )
        )
    )
    service._estates = SimpleNamespace(
        get_by_id=AsyncMock(return_value=SimpleNamespace(estate_id=1, name="Silverleaf Reserve"))
    )
    service._records = SimpleNamespace(
        facts=AsyncMock(
            return_value={
                "counts": {"open_complaints": 0, "work_orders_in_flight": 0, "unresolved_incidents": 0},
                "latest_score": {"overall_score": 88},
            }
        ),
        resident_signals=AsyncMock(
            return_value=[
                {"id": 42, "category": "Plumbing", "title": "Kitchen faucet leaking", "status": "reviewed", "logged_date": "2026-10-20"}
            ]
        ),
    )
    actor = SimpleNamespace(user_id=10, role="resident")
    res = await service.get_intelligence(1, actor)

    assert res.role == "resident"
    assert res.recommendations == []
    assert res.resident_view is not None
    assert len(res.resident_view.unit_issues) == 1
    assert res.resident_view.unit_issues[0].title == "Kitchen faucet leaking"
    assert res.resident_view.living_score_label == "Optimal"
    assert "88/100" in res.resident_view.living_score_summary


@pytest.mark.asyncio
async def test_provider_receives_provider_view_with_work_orders():
    service = IntelligenceService(AsyncMock())
    service._auth = SimpleNamespace(
        resolve_access=AsyncMock(
            return_value=SimpleNamespace(
                is_estate_admin=False,
                is_estate_provider=True,
                membership_roles=frozenset({"service_provider"}),
            )
        )
    )
    service._estates = SimpleNamespace(
        get_by_id=AsyncMock(return_value=SimpleNamespace(estate_id=1, name="Silverleaf Reserve"))
    )
    service._records = SimpleNamespace(
        facts=AsyncMock(
            return_value={
                "counts": {"open_complaints": 2, "work_orders_in_flight": 1, "unresolved_incidents": 0},
                "latest_score": None,
            }
        ),
        provider_signals=AsyncMock(
            return_value=[
                {
                    "id": 99,
                    "title": "Work Order #99",
                    "priority": "high",
                    "status": "assigned",
                    "location": "Gatehouse generator",
                    "due_date": "2026-10-25T12:00:00Z",
                }
            ]
        ),
    )
    actor = SimpleNamespace(user_id=20, role="service_provider")
    res = await service.get_intelligence(1, actor)

    assert res.role == "service_provider"
    assert res.recommendations == []
    assert res.provider_view is not None
    assert len(res.provider_view.assigned_work_orders) == 1
    assert res.provider_view.assigned_work_orders[0].id == 99
    assert res.provider_view.urgent_count == 1
    assert "Contractor site access" in res.provider_view.instructions


@pytest.mark.asyncio
async def test_stream_ask_valora_yields_sse_chunks():
    service = IntelligenceService(AsyncMock())
    service._auth = SimpleNamespace(
        resolve_access=AsyncMock(
            return_value=SimpleNamespace(
                is_estate_admin=False,
                is_estate_provider=False,
                membership_roles=frozenset({"resident"}),
            )
        )
    )
    service._estates = SimpleNamespace(
        get_by_id=AsyncMock(return_value=SimpleNamespace(estate_id=1, name="Silverleaf Reserve"))
    )
    service._records = SimpleNamespace(
        facts=AsyncMock(
            return_value={
                "counts": {"open_complaints": 0, "work_orders_in_flight": 0, "unresolved_incidents": 0},
                "latest_score": None,
                "previous_score": None,
            }
        ),
        resident_signals=AsyncMock(return_value=[]),
    )
    actor = SimpleNamespace(user_id=10, role="resident")
    generator = await service.stream_ask_valora(1, "What are the quiet hours?", actor)

    chunks = []
    async for chunk in generator:
        chunks.append(chunk)

    assert len(chunks) > 0
    # Every chunk should start with data:
    assert all(c.startswith("data: ") for c in chunks)
    # The last chunk should be [DONE]
    assert chunks[-1] == "data: [DONE]\n\n"
    # Content chunk must parse JSON with delta
    first_data = json.loads(chunks[0].replace("data: ", "").strip())
    assert "delta" in first_data

    # Multi-turn history support
    history = [
        {"role": "user", "content": "Hello VALORA"},
        {"role": "assistant", "content": "Hello! How can I assist you with your estate today?"},
    ]
    gen2 = await service.stream_ask_valora(1, "Tell me about noise rules", actor, history=history)
    chunks2 = [c async for c in gen2]
    assert len(chunks2) > 0
    assert chunks2[-1] == "data: [DONE]\n\n"
