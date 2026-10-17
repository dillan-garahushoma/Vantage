"""Tests for the VALORA Intelligence schemas, domain logic, and API contract."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.analytics.schemas.intelligence import (
    AskValoraRequest,
    AskValoraResponse,
    EstateIntelligenceResponse,
    OperationalSignalCounts,
    PriorityRecommendation,
    RecommendationEvidence,
    WeeklyBriefing,
    WorkOrderDefaults,
)
from app.analytics.services.intelligence_service import _default_recommendations, _domain_answer
from app.main import app


def test_priority_recommendations_schema_valid() -> None:
    recs = _default_recommendations()
    assert len(recs) == 3
    assert recs[0].id == "AI-01"
    assert recs[0].kind == "PREVENTIVE MAINTENANCE"
    assert recs[0].confidence == "High"
    assert recs[0].confidence_value == 91
    assert recs[0].savings_zar == 42000.0
    assert recs[0].work_order_defaults.priority == "high"


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


def test_domain_answers_coverage() -> None:
    # 1. health score question
    ans1 = _domain_answer("Why did our estate health score change?", "Greenhaven Estate")
    assert ans1.source == "estate-domain"
    assert "score moved because" in ans1.summary.lower()
    assert len(ans1.evidence) >= 3
    assert len(ans1.recommendation) > 10

    # 2. attention next month question
    ans2 = _domain_answer("What is likely to need attention next month?", "Greenhaven Estate")
    assert ans2.source == "estate-domain"
    assert "november" in ans2.summary.lower() or "reactive spend" in ans2.summary.lower()
    assert any("Pool Pump 02" in ev for ev in ans2.evidence)

    # 3. board question
    ans3 = _domain_answer("Summarise infrastructure risks for the board.", "Greenhaven Estate")
    assert ans3.source == "estate-domain"
    assert "water and pumping" in ans3.summary.lower()

    # 4. generic fallback
    ans4 = _domain_answer("Can we repair the clubhouse gate?", "Greenhaven Estate")
    assert ans4.source == "estate-domain"
    assert "scoped to greenhaven estate" in ans4.summary.lower()


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

    assert "/api/v1/analytics/intelligence/signals" in paths
    assert "get" in paths["/api/v1/analytics/intelligence/signals"]

    assert "/api/v1/analytics/intelligence/briefing" in paths
    assert "post" in paths["/api/v1/analytics/intelligence/briefing"]


def test_estate_signal_items_mapping() -> None:
    from app.analytics.models.living_score_snapshot import LivingScoreSnapshot
    from app.community.models.security_incident import SecurityIncident
    from app.community.models.maintenance_work_order import MaintenanceworkOrder
    from app.community.models.complaint import Complaint
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

