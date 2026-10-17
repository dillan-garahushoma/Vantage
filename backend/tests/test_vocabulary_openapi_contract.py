"""BATCH BE-1: the fixed triage vocabulary must be published in the contract.

``app/community/domain/triage_vocabulary.py`` is the single source of truth for
what a triage suggestion may say, and now also for what a new complaint may be
filed as. These tests fail if a DTO stops deriving its allowed values from those
tuples, or if the published contract ever drifts from them.
"""
from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.community.domain.triage_vocabulary import (
    CATEGORIES,
    DECISIONS,
    PRIORITIES,
    TRADES,
)
from app.community.schemas.complaint import ComplaintResponse
from app.community.services.complaint_service import ComplaintService
from app.db.session import get_db
from app.identity.api.dependencies import get_current_user
from app.main import app

client = TestClient(app)


def _resolve(node: dict) -> dict:
    """Follow a ``$ref`` so a named component is read as directly as an inline one."""
    ref = node.get("$ref")
    if ref:
        return app.openapi()["components"]["schemas"][ref.rsplit("/", 1)[-1]]
    return node


def _enum_values(schema_name: str, field: str) -> list[str]:
    node = _resolve(app.openapi()["components"]["schemas"][schema_name]["properties"][field])
    for branch in (node, *node.get("anyOf", []), *node.get("oneOf", [])):
        branch = _resolve(branch)
        if "enum" in branch:
            return list(branch["enum"])
    raise AssertionError(f"no enum published for {schema_name}.{field}: {node}")


def test_triage_decision_request_publishes_the_vocabulary() -> None:
    assert _enum_values("TriageDecisionRequest", "category") == list(CATEGORIES)
    assert _enum_values("TriageDecisionRequest", "priority") == list(PRIORITIES)
    assert _enum_values("TriageDecisionRequest", "trade") == list(TRADES)
    assert _enum_values("TriageDecisionRequest", "decision") == list(DECISIONS)


def test_triage_suggestion_response_publishes_the_vocabulary() -> None:
    for field, values in (
        ("suggested_category", CATEGORIES),
        ("suggested_priority", PRIORITIES),
        ("suggested_trade", TRADES),
        ("decided_category", CATEGORIES),
        ("decided_priority", PRIORITIES),
        ("decided_trade", TRADES),
    ):
        assert _enum_values("TriageSuggestionResponse", field) == list(values), field


def test_complaint_create_publishes_the_vocabulary() -> None:
    assert _enum_values("ComplaintCreate", "category") == list(CATEGORIES)
    assert _enum_values("ComplaintCreate", "priority") == list(PRIORITIES)


def test_complaint_responses_stay_free_text_so_legacy_rows_still_read() -> None:
    for field in ("category", "priority"):
        node = _resolve(
            app.openapi()["components"]["schemas"]["ComplaintResponse"]["properties"][field]
        )
        assert "enum" not in node, field
        assert all("enum" not in branch for branch in node.get("anyOf", [])), field


def _override_auth(role: str = "resident") -> dict:
    """Serve requests without a database or a token; returns the previous overrides."""
    original = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(user_id=1, role=role)
    return original


def test_complaint_create_rejects_values_outside_the_vocabulary() -> None:
    original = _override_auth()
    try:
        for field, value in (("category", "plumbing"), ("priority", "catastrophic")):
            body = {"unit_id": 1, "category": "water", "description": "Burst pipe in the garden."}
            body[field] = value
            response = client.post("/api/v1/complaints?estate_id=1", json=body)

            assert response.status_code == 422, (field, response.text)
            error = response.json()["detail"]
            assert error["code"] == "VALIDATION_ERROR"
            assert any(item["loc"][-1] == field for item in error["details"]), error
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)


def test_every_published_vocabulary_value_is_accepted_on_create(monkeypatch) -> None:
    async def _stub(self, payload, user, *, estate_id):
        return ComplaintResponse(
            complaint_id=1,
            user_id=1,
            estate_id=estate_id,
            unit_id=payload.unit_id,
            category=payload.category,
            description=payload.description,
            priority=payload.priority,
            is_anonymous=False,
            status="submitted",
            assigned_to=None,
            reviewed_at=None,
            assigned_at=None,
            started_at=None,
            resolved_at=None,
            created_at=None,
            updated_at=None,
        )

    monkeypatch.setattr(ComplaintService, "create_complaint", _stub)
    original = _override_auth()
    try:
        for category in CATEGORIES:
            response = client.post(
                "/api/v1/complaints?estate_id=1",
                json={
                    "unit_id": 1,
                    "category": category,
                    "description": "Burst pipe in the garden.",
                },
            )
            assert response.status_code == 201, (category, response.text)
            assert response.json()["category"] == category

        for priority in PRIORITIES:
            response = client.post(
                "/api/v1/complaints?estate_id=1",
                json={
                    "unit_id": 1,
                    "category": "water",
                    "description": "Burst pipe in the garden.",
                    "priority": priority,
                },
            )
            assert response.status_code == 201, (priority, response.text)
            assert response.json()["priority"] == priority
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)
