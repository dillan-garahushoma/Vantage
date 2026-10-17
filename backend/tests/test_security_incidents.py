"""BATCH 6B — intentionally limited security incidents.

Two layers, as in `test_announcements_estate_scoping.py`:

* **Vocabulary, schema, query-shape and policy tests** run everywhere, without a
  database.
* **Isolation tests** (`@pytest.mark.integration`) carry the cross-estate claims,
  because `valora-testing` says a fake built with `Class.__new__` cannot prove
  tenant isolation. They auto-skip when `TEST_DATABASE_URL` is unset.
"""
from __future__ import annotations

import inspect
import os
import subprocess
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import CheckConstraint, ForeignKeyConstraint
from sqlalchemy.dialects import sqlite

from app.common.enums import UserRole
from app.common.pagination import Page
from app.community.domain import incident_vocabulary as vocab
from app.community.models.security_incident import SecurityIncident
from app.community.repositories.security_incident_repository import (
    SecurityIncidentRepository,
)
from app.community.schemas.security_incident import (
    IncidentCreate,
    IncidentResponse,
    IncidentUpdate,
)
from app.community.services.security_incident_service import SecurityIncidentService
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.core.security import create_access_token
from app.db.session import get_db
from app.identity.api.dependencies import get_current_user
from app.identity.models.user import User
from app.identity.repositories.user_repository import UserRepository
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.main import app

BACKEND_DIR = Path(__file__).resolve().parent.parent
PARENT_REVISION = "b8e5f2d1c3a4"  # the head this batch migrates from
MIGRATION_FILE = (
    BACKEND_DIR / "alembic" / "versions" / "a7c1e9d4f6b2_add_security_incidents.py"
)

COLLECTION_PATH = "/api/v1/incidents"
client = TestClient(app)


# --------------------------------------------------------------------------- #
# Test doubles: policy and query shape only - never isolation.
# --------------------------------------------------------------------------- #
class _EmptyResult:
    def scalars(self):
        return self

    def all(self):
        return []

    def scalar_one(self):
        return 0

    def scalar_one_or_none(self):
        return None


class RecordingSession:
    def __init__(self) -> None:
        self.statements: list = []

    async def execute(self, statement):
        self.statements.append(statement)
        return _EmptyResult()


class FakeMembershipRepo:
    def __init__(self, memberships: list) -> None:
        self.memberships = memberships

    async def list_for_user_and_estate(self, *, user_id: int, estate_id: int):
        return [
            m for m in self.memberships if m.user_id == user_id and m.estate_id == estate_id
        ]

    async def get_for_user_and_estate(self, *, user_id: int, estate_id: int):
        matches = await self.list_for_user_and_estate(user_id=user_id, estate_id=estate_id)
        return matches[0] if matches else None


def _auth_service(memberships: list) -> EstateAuthorizationService:
    service = EstateAuthorizationService.__new__(EstateAuthorizationService)
    service._memberships = FakeMembershipRepo(memberships)
    return service


def _membership(user_id: int, estate_id: int, role: str, property_id: int | None = None):
    return SimpleNamespace(
        user_id=user_id, estate_id=estate_id, property_id=property_id, membership_role=role
    )


def _estate_admin(estate_id: int, user_id: int = 22):
    return (
        SimpleNamespace(user_id=user_id, role=UserRole.hoa_admin.value),
        [_membership(user_id, estate_id, UserRole.hoa_admin.value)],
    )


def _resident(estate_id: int, user_id: int = 21):
    return (
        SimpleNamespace(user_id=user_id, role=UserRole.resident.value),
        [_membership(user_id, estate_id, UserRole.resident.value, property_id=1)],
    )


def _incident(
    *,
    estate_id: int = 5,
    status: str = "open",
    severity: str = "medium",
    category: str = "theft",
    property_id: int | None = 41,
    resolution_notes: str | None = None,
    created_by: int | None = 22,
    occurred_at: datetime | None = None,
    resolved_at: datetime | None = None,
):
    return SimpleNamespace(
        incident_id=77,
        estate_id=estate_id,
        property_id=property_id,
        category=category,
        severity=severity,
        status=status,
        occurred_at=occurred_at or datetime(2026, 9, 1, tzinfo=timezone.utc),
        resolved_at=resolved_at,
        resolution_notes=resolution_notes,
        created_by=created_by,
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )


class RecordingIncidentRepo:
    """Records calls and refuses any delete-shaped method."""

    def __init__(self, *, by_id=None, items: list | None = None, total: int = 0) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._by_id = by_id
        self._items = items or []
        self._total = total

    async def create(self, **kwargs):
        self.calls.append(("create", kwargs))
        return _incident(**kwargs)

    async def get_by_id_in_estate(self, **kwargs):
        self.calls.append(("get_by_id_in_estate", kwargs))
        return self._by_id

    async def search(self, **kwargs):
        self.calls.append(("search", kwargs))
        return self._items

    async def count(self, **kwargs):
        self.calls.append(("count", kwargs))
        return self._total

    async def save(self, incident):
        self.calls.append(("save", {}))
        return incident

    async def count_in_window(self, **kwargs):
        self.calls.append(("count_in_window", kwargs))
        return 0

    def delete(self, *args, **kwargs):  # pragma: no cover - must never exist
        raise AssertionError("incidents must not be deletable")

    def kwargs_for(self, method: str) -> dict:
        return next(kwargs for name, kwargs in self.calls if name == method)


class FakePropertyRepo:
    def __init__(self, *, unit_ids_in_estate: set[int] | None = None) -> None:
        self.calls: list[dict] = []
        self._unit_ids = unit_ids_in_estate or set()

    async def get_by_id_in_estate(self, *, unit_id: int, estate_id: int):
        self.calls.append({"unit_id": unit_id, "estate_id": estate_id})
        if unit_id in self._unit_ids:
            return SimpleNamespace(unit_id=unit_id, estate_id=estate_id)
        return None


def _service(repo, memberships: list, *, properties: set[int] | None = None):
    service = SecurityIncidentService.__new__(SecurityIncidentService)
    service._repo = repo
    service._estate_authorization = _auth_service(memberships)
    service._property_repo = FakePropertyRepo(unit_ids_in_estate=properties or set())
    return service


def _create_payload(**overrides) -> IncidentCreate:
    payload = {
        "category": "theft",
        "severity": "high",
        "occurred_at": datetime.now(timezone.utc) - timedelta(hours=2),
    }
    payload.update(overrides)
    return IncidentCreate.model_validate(payload)


# --------------------------------------------------------------------------- #
# Vocabulary
# --------------------------------------------------------------------------- #
def test_vocabulary_matches_the_batch() -> None:
    assert vocab.CATEGORIES == (
        "perimeter_breach",
        "access_control_failure",
        "theft",
        "vandalism",
        "trespass",
        "suspicious_activity",
        "other",
    )
    assert vocab.SEVERITIES == ("low", "medium", "high", "critical")
    assert vocab.STATUSES == ("open", "investigating", "resolved")


def test_vocabulary_has_no_duplicates_and_no_blank_values() -> None:
    for values in (vocab.CATEGORIES, vocab.SEVERITIES, vocab.STATUSES):
        assert len(set(values)) == len(values)
        for value in values:
            assert value == value.strip()
            assert value
            assert value == value.lower()


def test_membership_helpers() -> None:
    assert vocab.is_valid_category("theft") is True
    assert vocab.is_valid_category("burglary") is False
    assert vocab.is_valid_category(None) is False
    assert vocab.is_valid_severity("critical") is True
    assert vocab.is_valid_severity("urgent") is False
    assert vocab.is_valid_status("investigating") is True
    assert vocab.is_valid_status("closed") is False


def test_vocabulary_is_dependency_free() -> None:
    """The vocabulary must not import anything from the application."""
    source = (BACKEND_DIR / "app" / "community" / "domain" / "incident_vocabulary.py").read_text(
        encoding="utf-8"
    )

    assert "from app." not in source
    assert "import app." not in source


def test_sql_renderers_quote_every_value() -> None:
    rendered = vocab.sql_in("category", vocab.CATEGORIES)
    nullable = vocab.nullable_sql_in("severity", vocab.SEVERITIES)

    assert rendered.startswith("category IN (") and rendered.endswith(")")
    for value in vocab.CATEGORIES:
        assert f"'{value}'" in rendered
    assert nullable.startswith("severity IS NULL OR severity IN (")


# --------------------------------------------------------------------------- #
# Model and migration
# --------------------------------------------------------------------------- #
def test_incident_table_shape() -> None:
    columns = SecurityIncident.__table__.c

    assert SecurityIncident.__tablename__ == "security_incidents"
    assert set(columns.keys()) == {
        "incident_id",
        "estate_id",
        "property_id",
        "category",
        "severity",
        "status",
        "occurred_at",
        "resolved_at",
        "resolution_notes",
        "created_by",
        "created_at",
        "updated_at",
    }
    for name in (
        "incident_id",
        "estate_id",
        "category",
        "severity",
        "status",
        "occurred_at",
        "created_at",
        "updated_at",
    ):
        assert columns[name].nullable is False, name
    for name in ("property_id", "resolved_at", "resolution_notes", "created_by"):
        assert columns[name].nullable is True, name


def test_foreign_keys_use_the_right_delete_actions() -> None:
    foreign_keys = {
        fk.name: fk
        for fk in SecurityIncident.__table__.constraints
        if isinstance(fk, ForeignKeyConstraint)
    }
    actions = {name: fk.ondelete for name, fk in foreign_keys.items()}

    assert actions == {
        "fk_security_incidents_estate_id_estates": "RESTRICT",
        "fk_security_incidents_property_id_properties": "SET NULL",
        "fk_security_incidents_created_by_users": "SET NULL",
    }


def test_check_constraints_are_built_from_the_vocabulary() -> None:
    checks = {
        c.name: str(c.sqltext)
        for c in SecurityIncident.__table__.constraints
        if isinstance(c, CheckConstraint)
    }

    assert set(checks) == {
        "ck_security_incidents_category",
        "ck_security_incidents_severity",
        "ck_security_incidents_status",
        "ck_security_incidents_resolution_timestamps",
    }
    for value in vocab.CATEGORIES:
        assert f"'{value}'" in checks["ck_security_incidents_category"]
    for value in vocab.SEVERITIES:
        assert f"'{value}'" in checks["ck_security_incidents_severity"]
    for value in vocab.STATUSES:
        assert f"'{value}'" in checks["ck_security_incidents_status"]
    assert "(status = 'resolved') = (resolved_at IS NOT NULL)" in (
        checks["ck_security_incidents_resolution_timestamps"].replace('"', "'")
    )


def test_the_migration_builds_its_constraints_from_the_vocabulary() -> None:
    """Drift guard: the migration must not hardcode its own value lists."""
    source = MIGRATION_FILE.read_text(encoding="utf-8")

    assert "from app.community.domain.incident_vocabulary import" in source
    for value in vocab.CATEGORIES + vocab.SEVERITIES + vocab.STATUSES:
        assert f'"{value}"' not in source, value
    for name in (
        "security_incidents",
        "fk_security_incidents_estate_id_estates",
        "fk_security_incidents_property_id_properties",
        "fk_security_incidents_created_by_users",
        "ck_security_incidents_resolution_timestamps",
        "ix_security_incidents_estate_id_occurred_at",
        "ix_security_incidents_estate_id_status",
    ):
        assert name in source, name


def test_indexes_cover_the_score_window_and_the_status_filter() -> None:
    indexes = {
        index.name: [c.name for c in index.columns]
        for index in SecurityIncident.__table__.indexes
    }

    assert indexes["ix_security_incidents_estate_id_occurred_at"] == [
        "estate_id",
        "occurred_at",
    ]
    assert indexes["ix_security_incidents_estate_id_status"] == ["estate_id", "status"]


def _offline_sql(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", *args],
        cwd=str(BACKEND_DIR),
        env=dict(os.environ),
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_offline_upgrade_sql_creates_the_incident_table() -> None:
    result = _offline_sql("upgrade", "head", "--sql")

    assert result.returncode == 0, result.stderr
    sql = result.stdout
    assert "CREATE TABLE security_incidents" in sql
    assert "fk_security_incidents_estate_id_estates" in sql
    assert "fk_security_incidents_property_id_properties" in sql
    assert "fk_security_incidents_created_by_users" in sql
    assert "ck_security_incidents_category" in sql
    assert "ck_security_incidents_resolution_timestamps" in sql
    assert "CREATE INDEX ix_security_incidents_estate_id_occurred_at" in sql
    assert "CREATE INDEX ix_security_incidents_estate_id_status" in sql


def test_offline_downgrade_sql_reverses_this_migration() -> None:
    result = _offline_sql("downgrade", f"head:{PARENT_REVISION}", "--sql")

    assert result.returncode == 0, result.stderr
    assert "DROP TABLE security_incidents" in result.stdout


# --------------------------------------------------------------------------- #
# Schema and API contract
# --------------------------------------------------------------------------- #
def test_request_dtos_forbid_unknown_fields() -> None:
    for model in (IncidentCreate, IncidentUpdate):
        assert model.model_config.get("extra") == "forbid", model.__name__

    with pytest.raises(ValidationError):
        IncidentCreate.model_validate(
            {
                "category": "theft",
                "severity": "high",
                "occurred_at": datetime.now(timezone.utc),
                "estate_id": 999,
            }
        )
    with pytest.raises(ValidationError):
        IncidentUpdate.model_validate({"category": "vandalism"})


def test_update_dto_exposes_only_the_patchable_fields() -> None:
    assert set(IncidentUpdate.model_fields) == {"severity", "status", "resolution_notes"}


def test_vocabulary_values_are_enforced_by_the_dtos() -> None:
    with pytest.raises(ValidationError):
        IncidentCreate.model_validate(
            {
                "category": "burglary",
                "severity": "high",
                "occurred_at": datetime.now(timezone.utc),
            }
        )
    with pytest.raises(ValidationError):
        IncidentUpdate.model_validate({"severity": "urgent"})
    with pytest.raises(ValidationError):
        IncidentUpdate.model_validate({"status": "closed"})

    assert IncidentUpdate.model_validate({"severity": "critical"}).severity == "critical"


def test_response_dto_carries_the_admin_only_fields() -> None:
    # serialization mode, because the wire contract uses the `id` alias
    properties = set(IncidentResponse.model_json_schema(mode="serialization")["properties"])

    assert properties == {
        "id",
        "estate_id",
        "category",
        "severity",
        "status",
        "occurred_at",
        "resolved_at",
        "property_id",
        "resolution_notes",
        "created_by",
        "created_at",
        "updated_at",
    }


def test_the_routes_are_registered_without_a_delete() -> None:
    paths = app.openapi()["paths"]

    assert set(paths[COLLECTION_PATH]) == {"get", "post"}
    assert set(paths[f"{COLLECTION_PATH}/{{incident_id}}"]) == {"get", "patch"}


def test_no_http_route_allows_deleting_an_incident() -> None:
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith(COLLECTION_PATH):
            assert "DELETE" not in (getattr(route, "methods", set()) or set()), path


def test_the_repository_has_no_delete_method() -> None:
    source = inspect.getsource(SecurityIncidentRepository)

    assert "def delete" not in source
    assert not hasattr(SecurityIncidentRepository, "delete")


def test_incidents_list_enforces_pagination_bounds() -> None:
    admin = SimpleNamespace(user_id=1, role=UserRole.hoa_admin.value)

    def action():
        assert client.get(f"{COLLECTION_PATH}?estate_id=1&page=0").status_code == 422
        assert client.get(f"{COLLECTION_PATH}?estate_id=1&size=0").status_code == 422
        assert client.get(f"{COLLECTION_PATH}?estate_id=1&size=101").status_code == 422
        assert client.get(f"{COLLECTION_PATH}?size=20").status_code == 422
        assert client.get(f"{COLLECTION_PATH}?estate_id=0").status_code == 422

    _run_with(_override(admin), action)


def test_incidents_list_rejects_filters_outside_the_vocabulary() -> None:
    admin = SimpleNamespace(user_id=1, role=UserRole.hoa_admin.value)

    def action():
        assert client.get(f"{COLLECTION_PATH}?estate_id=1&status=closed").status_code == 422
        assert client.get(f"{COLLECTION_PATH}?estate_id=1&severity=urgent").status_code == 422
        assert client.get(f"{COLLECTION_PATH}?estate_id=1&category=burglary").status_code == 422

    _run_with(_override(admin), action)


def test_incidents_list_passes_filters_through_to_the_service(monkeypatch) -> None:
    captured: dict = {}

    async def fake_list(self, user, **kwargs):
        captured.update(kwargs)
        return Page[IncidentResponse](items=[], total=0, page=2, size=10)

    monkeypatch.setattr(SecurityIncidentService, "list_incidents", fake_list)
    admin = SimpleNamespace(user_id=1, role=UserRole.hoa_admin.value)

    def action():
        response = client.get(
            f"{COLLECTION_PATH}?estate_id=3&page=2&size=10&status=open"
            "&severity=high&category=theft"
            "&occurred_from=2026-01-01T00:00:00Z&occurred_to=2026-02-01T00:00:00Z"
        )
        assert response.status_code == 200, response.text

    _run_with(_override(admin), action)

    assert captured["estate_id"] == 3
    assert captured["page"] == 2 and captured["size"] == 10
    assert captured["status"] == "open"
    assert captured["severity"] == "high"
    assert captured["category"] == "theft"
    assert captured["occurred_from"] == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert captured["occurred_to"] == datetime(2026, 2, 1, tzinfo=timezone.utc)


def test_resident_cannot_create_or_update_incidents() -> None:
    resident = SimpleNamespace(user_id=5, role=UserRole.resident.value)
    body = {
        "category": "theft",
        "severity": "high",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }

    def action():
        assert client.post(f"{COLLECTION_PATH}?estate_id=1", json=body).status_code == 403
        assert (
            client.patch(f"{COLLECTION_PATH}/9?estate_id=1", json={"severity": "low"}).status_code
            == 403
        )

    _run_with(_override(resident), action)


def test_create_takes_the_estate_from_the_query_and_the_author_from_the_token(
    monkeypatch,
) -> None:
    captured: dict = {}

    async def fake_create(self, payload, admin, *, estate_id: int):
        captured["estate_id"] = estate_id
        captured["admin_id"] = admin.user_id
        return IncidentResponse(
            incident_id=1,
            estate_id=estate_id,
            category=payload.category,
            severity=payload.severity,
            status="open",
            occurred_at=payload.occurred_at,
            resolved_at=None,
            property_id=None,
            resolution_notes=None,
            created_by=admin.user_id,
            created_at=None,
            updated_at=None,
        )

    monkeypatch.setattr(SecurityIncidentService, "create_incident", fake_create)
    admin = SimpleNamespace(user_id=77, role=UserRole.hoa_admin.value)

    def action():
        response = client.post(
            f"{COLLECTION_PATH}?estate_id=2",
            json={
                "category": "theft",
                "severity": "high",
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["estate_id"] == 2

    _run_with(_override(admin), action)

    assert captured == {"estate_id": 2, "admin_id": 77}


# --------------------------------------------------------------------------- #
# Service rules
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_create_requires_the_hoa_admin_role_in_that_estate() -> None:
    repo = RecordingIncidentRepo()
    actor, memberships = _resident(estate_id=5)

    with pytest.raises(ForbiddenException):
        await _service(repo, memberships).create_incident(
            _create_payload(), actor, estate_id=5
        )

    assert repo.calls == []


@pytest.mark.asyncio
async def test_update_requires_the_estate_admin_role() -> None:
    repo = RecordingIncidentRepo(by_id=_incident())
    actor, memberships = _resident(estate_id=5)

    with pytest.raises(ForbiddenException):
        await _service(repo, memberships).update_incident(
            77, IncidentUpdate(severity="low"), actor, estate_id=5
        )


@pytest.mark.asyncio
async def test_create_starts_open_and_stores_the_admin_as_author() -> None:
    repo = RecordingIncidentRepo()
    admin, memberships = _estate_admin(estate_id=5, user_id=22)

    await _service(repo, memberships).create_incident(_create_payload(), admin, estate_id=5)

    created = repo.kwargs_for("create")
    assert created["estate_id"] == 5
    assert created["created_by"] == 22
    assert created["status"] == "open"


@pytest.mark.asyncio
async def test_create_rejects_a_future_occurred_at() -> None:
    future = datetime.now(timezone.utc) + timedelta(hours=3)

    with pytest.raises(ValidationError):
        _create_payload(occurred_at=future)


@pytest.mark.asyncio
async def test_create_allows_a_few_minutes_of_clock_skew() -> None:
    payload = _create_payload(occurred_at=datetime.now(timezone.utc) + timedelta(minutes=2))

    assert payload.occurred_at is not None


@pytest.mark.asyncio
async def test_create_normalises_occurred_at_to_utc() -> None:
    payload = _create_payload(
        occurred_at=datetime(2026, 9, 1, 12, 0, tzinfo=timezone(timedelta(hours=2)))
    )

    assert payload.occurred_at == datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_create_rejects_a_property_from_another_estate() -> None:
    repo = RecordingIncidentRepo()
    admin, memberships = _estate_admin(estate_id=5)
    service = _service(repo, memberships, properties={41})

    with pytest.raises(NotFoundException):
        await service.create_incident(_create_payload(property_id=999), admin, estate_id=5)

    assert repo.calls == []
    assert service._property_repo.calls == [{"unit_id": 999, "estate_id": 5}]


@pytest.mark.asyncio
async def test_create_accepts_a_property_in_the_estate() -> None:
    repo = RecordingIncidentRepo()
    admin, memberships = _estate_admin(estate_id=5)
    service = _service(repo, memberships, properties={41})

    await service.create_incident(_create_payload(property_id=41), admin, estate_id=5)

    assert repo.kwargs_for("create")["property_id"] == 41


@pytest.mark.asyncio
async def test_open_can_move_to_investigating() -> None:
    incident = _incident(status="open")
    repo = RecordingIncidentRepo(by_id=incident)
    admin, memberships = _estate_admin(estate_id=5)

    response = await _service(repo, memberships).update_incident(
        77, IncidentUpdate(status="investigating"), admin, estate_id=5
    )

    assert incident.status == "investigating"
    assert incident.resolved_at is None
    assert response.status == "investigating"


@pytest.mark.asyncio
async def test_open_can_move_straight_to_resolved_and_gets_a_server_side_timestamp() -> None:
    incident = _incident(status="open")
    repo = RecordingIncidentRepo(by_id=incident)
    admin, memberships = _estate_admin(estate_id=5)

    await _service(repo, memberships).update_incident(
        77, IncidentUpdate(status="resolved"), admin, estate_id=5
    )

    assert incident.status == "resolved"
    assert incident.resolved_at is not None
    assert incident.resolved_at.tzinfo is not None


@pytest.mark.asyncio
async def test_investigating_cannot_go_back_to_open() -> None:
    incident = _incident(status="investigating")
    repo = RecordingIncidentRepo(by_id=incident)
    admin, memberships = _estate_admin(estate_id=5)

    with pytest.raises(ConflictException):
        await _service(repo, memberships).update_incident(
            77, IncidentUpdate(status="open"), admin, estate_id=5
        )

    assert incident.status == "investigating"


@pytest.mark.asyncio
async def test_resolved_is_terminal() -> None:
    incident = _incident(
        status="resolved",
        resolved_at=datetime(2026, 9, 2, tzinfo=timezone.utc),
    )
    repo = RecordingIncidentRepo(by_id=incident)
    admin, memberships = _estate_admin(estate_id=5)

    for payload in (
        IncidentUpdate(status="investigating"),
        IncidentUpdate(severity="low"),
        IncidentUpdate(resolution_notes="Corrected."),
    ):
        with pytest.raises(ConflictException):
            await _service(repo, memberships).update_incident(77, payload, admin, estate_id=5)

    assert incident.severity == "medium"
    assert incident.resolution_notes is None


@pytest.mark.asyncio
async def test_severity_and_notes_can_be_patched_before_resolution() -> None:
    incident = _incident(status="investigating")
    repo = RecordingIncidentRepo(by_id=incident)
    admin, memberships = _estate_admin(estate_id=5)

    await _service(repo, memberships).update_incident(
        77,
        IncidentUpdate(severity="critical", resolution_notes="Waiting on the gate vendor."),
        admin,
        estate_id=5,
    )

    assert incident.severity == "critical"
    assert incident.resolution_notes == "Waiting on the gate vendor."
    assert incident.status == "investigating"


@pytest.mark.asyncio
async def test_update_is_estate_scoped_on_the_read() -> None:
    repo = RecordingIncidentRepo(by_id=_incident(estate_id=5))
    admin, memberships = _estate_admin(estate_id=5)

    await _service(repo, memberships).update_incident(
        77, IncidentUpdate(severity="low"), admin, estate_id=5
    )

    assert repo.kwargs_for("get_by_id_in_estate") == {"incident_id": 77, "estate_id": 5}


@pytest.mark.asyncio
async def test_update_of_an_incident_from_another_estate_is_a_404() -> None:
    repo = RecordingIncidentRepo(by_id=None)
    admin, memberships = _estate_admin(estate_id=5)

    with pytest.raises(NotFoundException):
        await _service(repo, memberships).update_incident(
            77, IncidentUpdate(severity="low"), admin, estate_id=5
        )


@pytest.mark.asyncio
async def test_list_scopes_the_repository_calls_to_the_estate() -> None:
    repo = RecordingIncidentRepo()
    actor, memberships = _resident(estate_id=5)

    await _service(repo, memberships).list_incidents(
        actor,
        page=2,
        size=10,
        estate_id=5,
        status="open",
        severity="high",
        category="theft",
    )

    assert [name for name, _ in repo.calls] == ["search", "count"]
    for method in ("search", "count"):
        kwargs = repo.kwargs_for(method)
        assert kwargs["estate_id"] == 5
        assert kwargs["status"] == "open"
        assert kwargs["severity"] == "high"
        assert kwargs["category"] == "theft"
    assert repo.kwargs_for("search")["offset"] == 10
    assert repo.kwargs_for("search")["limit"] == 10


def test_a_non_admin_response_hides_the_admin_only_fields() -> None:
    response = SecurityIncidentService._to_response(_incident(), is_estate_admin=False)

    assert response.property_id is None
    assert response.resolution_notes is None
    assert response.created_by is None


def test_an_admin_response_keeps_the_admin_only_fields() -> None:
    response = SecurityIncidentService._to_response(
        _incident(resolution_notes="Gate repaired."), is_estate_admin=True
    )

    assert response.property_id == 41
    assert response.resolution_notes == "Gate repaired."
    assert response.created_by == 22


@pytest.mark.asyncio
async def test_get_returns_the_scoped_row_and_hides_fields_from_a_member() -> None:
    repo = RecordingIncidentRepo(by_id=_incident(resolution_notes="Gate repaired."))
    actor, memberships = _resident(estate_id=5)

    response = await _service(repo, memberships).get_incident(77, actor, estate_id=5)

    assert response.incident_id == 77
    assert response.resolution_notes is None
    assert repo.kwargs_for("get_by_id_in_estate") == {"incident_id": 77, "estate_id": 5}


# --------------------------------------------------------------------------- #
# Query shape: the estate filter and the score window, executed for real
# --------------------------------------------------------------------------- #
def _incidents_table() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE security_incidents (
            incident_id INTEGER PRIMARY KEY,
            estate_id INTEGER NOT NULL,
            property_id INTEGER NULL,
            category TEXT NOT NULL,
            severity TEXT NOT NULL,
            status TEXT NOT NULL,
            occurred_at TIMESTAMP NOT NULL,
            resolved_at TIMESTAMP NULL,
            resolution_notes TEXT NULL,
            created_by INTEGER NULL,
            created_at TIMESTAMP NULL,
            updated_at TIMESTAMP NULL
        )
        """
    )
    # estate 5: before the window, exactly at the start, inside, exactly at the end
    # estate 6: inside the window, to prove the estate filter is applied too
    rows = [
        (1, 5, "theft", "low", "open", "2026-08-31 23:59:59.000000"),
        (2, 5, "theft", "low", "resolved", "2026-09-01 00:00:00.000000"),
        (3, 5, "vandalism", "high", "open", "2026-09-15 12:00:00.000000"),
        (4, 5, "theft", "low", "open", "2026-10-01 00:00:00.000000"),
        (5, 6, "trespass", "low", "open", "2026-09-15 12:00:00.000000"),
    ]
    connection.executemany(
        "INSERT INTO security_incidents (incident_id, estate_id, category, severity, status,"
        " occurred_at) VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    connection.commit()
    return connection


def _compiled(statement) -> str:
    return str(statement.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}))


@pytest.mark.asyncio
async def test_count_in_window_is_inclusive_of_the_start_and_exclusive_of_the_end() -> None:
    session = RecordingSession()
    await SecurityIncidentRepository(session).count_in_window(
        estate_id=5,
        start=datetime(2026, 9, 1, tzinfo=timezone.utc),
        end=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )

    connection = _incidents_table()
    try:
        counted = connection.execute(_compiled(session.statements[0])).fetchone()[0]
    finally:
        connection.close()

    # 09-01 00:00 (start, inclusive) and 09-15 count; 08-31 and 10-01 (end) do not;
    # the estate 6 row is excluded by the estate filter.
    assert counted == 2


@pytest.mark.asyncio
async def test_count_in_window_ignores_status() -> None:
    session = RecordingSession()
    await SecurityIncidentRepository(session).count_in_window(
        estate_id=5,
        start=datetime(2026, 9, 1, tzinfo=timezone.utc),
        end=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )

    sql = _compiled(session.statements[0])
    assert "status" not in sql.lower()


@pytest.mark.asyncio
async def test_search_statement_filters_on_the_estate_and_the_window() -> None:
    session = RecordingSession()
    await SecurityIncidentRepository(session).search(
        offset=0,
        limit=20,
        estate_id=5,
        occurred_from=datetime(2026, 9, 1, tzinfo=timezone.utc),
        occurred_to=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )

    connection = _incidents_table()
    try:
        rows = connection.execute(_compiled(session.statements[0])).fetchall()
    finally:
        connection.close()

    assert [row[0] for row in rows] == [3, 2]


@pytest.mark.asyncio
async def test_count_uses_the_same_filters_as_search() -> None:
    session = RecordingSession()
    await SecurityIncidentRepository(session).count(
        estate_id=5,
        severity="high",
    )

    sql = _compiled(session.statements[0])
    assert "security_incidents.estate_id = 5" in sql
    assert "security_incidents.severity = 'high'" in sql


def test_the_repository_never_exposes_an_unscoped_getter() -> None:
    assert not hasattr(SecurityIncidentRepository, "get_by_id")


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #
def _override(user) -> dict:
    return {
        get_db: lambda: object(),
        get_current_user: lambda: SimpleNamespace(user_id=user.user_id, role=user.role),
    }


def _run_with(overrides: dict, action):
    original = app.dependency_overrides.copy()
    app.dependency_overrides.update(overrides)
    try:
        return action()
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)


def _bearer(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.user_id)})}"}


async def _seed_incident(session, *, estate_id, created_by, **overrides):
    incident = SecurityIncident(
        estate_id=estate_id,
        property_id=overrides.get("property_id"),
        category=overrides.get("category", "theft"),
        severity=overrides.get("severity", "medium"),
        status=overrides.get("status", "open"),
        occurred_at=overrides.get("occurred_at", datetime.now(timezone.utc)),
        resolved_at=overrides.get("resolved_at"),
        resolution_notes=overrides.get("resolution_notes"),
        created_by=created_by,
    )
    session.add(incident)
    await session.commit()
    await session.refresh(incident)
    return incident


# --------------------------------------------------------------------------- #
# Isolation: real database only. These auto-skip without TEST_DATABASE_URL.
# --------------------------------------------------------------------------- #
@pytest.mark.integration
@pytest.mark.asyncio
async def test_member_of_estate_a_cannot_list_estate_b_incidents(db_session, async_client) -> None:
    from tests.factories import build_two_estate_world

    world = await build_two_estate_world(db_session)
    await _seed_incident(
        db_session, estate_id=world.estate_b.estate_id, created_by=world.hoa_admin_b.user_id
    )

    response = await async_client.get(
        f"{COLLECTION_PATH}?estate_id={world.estate_b.estate_id}",
        headers=_bearer(world.resident_a1),
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_estate_a_member_reading_an_estate_b_incident_gets_404(
    db_session, async_client
) -> None:
    from tests.factories import build_two_estate_world

    world = await build_two_estate_world(db_session)
    foreign = await _seed_incident(
        db_session, estate_id=world.estate_b.estate_id, created_by=world.hoa_admin_b.user_id
    )

    response = await async_client.get(
        f"{COLLECTION_PATH}/{foreign.incident_id}?estate_id={world.estate_a.estate_id}",
        headers=_bearer(world.resident_a1),
    )

    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_hoa_admin_without_estate_membership_cannot_write_incidents(
    db_session, async_client
) -> None:
    from tests.factories import build_two_estate_world

    world = await build_two_estate_world(db_session)
    orphan = await UserRepository(db_session).create(
        full_name="Orphan Admin",
        email="orphan_incident_admin@valora.test",
        password_hash="not-a-real-hash",
        role=UserRole.hoa_admin.value,
    )
    # `UserRepository.create` does not take `hoa_approved`, so the flag is set on
    # the model. It gates no authorisation; this test only needs a global HOA admin.
    orphan.hoa_approved = True
    await db_session.commit()
    target = await _seed_incident(
        db_session, estate_id=world.estate_a.estate_id, created_by=world.hoa_admin_a.user_id
    )
    headers = _bearer(orphan)
    estate_id = world.estate_a.estate_id

    created = await async_client.post(
        f"{COLLECTION_PATH}?estate_id={estate_id}",
        json={
            "category": "theft",
            "severity": "high",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=headers,
    )
    updated = await async_client.patch(
        f"{COLLECTION_PATH}/{target.incident_id}?estate_id={estate_id}",
        json={"severity": "low"},
        headers=headers,
    )

    assert [created.status_code, updated.status_code] == [403, 403]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_resident_cannot_write_incidents_over_http(db_session, async_client) -> None:
    from tests.factories import build_two_estate_world

    world = await build_two_estate_world(db_session)
    target = await _seed_incident(
        db_session, estate_id=world.estate_a.estate_id, created_by=world.hoa_admin_a.user_id
    )
    headers = _bearer(world.resident_a1)
    estate_id = world.estate_a.estate_id

    created = await async_client.post(
        f"{COLLECTION_PATH}?estate_id={estate_id}",
        json={
            "category": "theft",
            "severity": "high",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=headers,
    )
    updated = await async_client.patch(
        f"{COLLECTION_PATH}/{target.incident_id}?estate_id={estate_id}",
        json={"severity": "low"},
        headers=headers,
    )

    assert [created.status_code, updated.status_code] == [403, 403]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_resident_response_hides_the_admin_only_fields(db_session, async_client) -> None:
    from tests.factories import build_two_estate_world

    world = await build_two_estate_world(db_session)
    incident = await _seed_incident(
        db_session,
        estate_id=world.estate_a.estate_id,
        created_by=world.hoa_admin_a.user_id,
        resolution_notes="Gate vendor booked.",
    )
    estate_id = world.estate_a.estate_id

    member_view = await async_client.get(
        f"{COLLECTION_PATH}/{incident.incident_id}?estate_id={estate_id}",
        headers=_bearer(world.resident_a1),
    )
    admin_view = await async_client.get(
        f"{COLLECTION_PATH}/{incident.incident_id}?estate_id={estate_id}",
        headers=_bearer(world.hoa_admin_a),
    )

    assert member_view.status_code == 200, member_view.text
    body = member_view.json()
    # the keys are present and null, as the contract says
    assert body["resolution_notes"] is None
    assert body["created_by"] is None
    assert body["property_id"] is None
    assert body["category"] == "theft"

    assert admin_view.status_code == 200, admin_view.text
    assert admin_view.json()["resolution_notes"] == "Gate vendor booked."
    assert admin_view.json()["created_by"] == world.hoa_admin_a.user_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_an_estate_admin_can_move_an_incident_to_resolved(db_session, async_client) -> None:
    from tests.factories import build_two_estate_world

    world = await build_two_estate_world(db_session)
    incident = await _seed_incident(
        db_session, estate_id=world.estate_a.estate_id, created_by=world.hoa_admin_a.user_id
    )

    response = await async_client.patch(
        f"{COLLECTION_PATH}/{incident.incident_id}?estate_id={world.estate_a.estate_id}",
        json={"status": "resolved", "resolution_notes": "Fence repaired."},
        headers=_bearer(world.hoa_admin_a),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "resolved"
    assert body["resolved_at"] is not None

    again = await async_client.patch(
        f"{COLLECTION_PATH}/{incident.incident_id}?estate_id={world.estate_a.estate_id}",
        json={"status": "investigating"},
        headers=_bearer(world.hoa_admin_a),
    )
    assert again.status_code == 409


@pytest.mark.integration
@pytest.mark.asyncio
async def test_count_in_window_is_estate_scoped_in_a_real_database(db_session) -> None:
    from tests.factories import build_two_estate_world

    world = await build_two_estate_world(db_session)
    window_start = datetime.now(timezone.utc) - timedelta(days=90)
    window_end = datetime.now(timezone.utc)
    inside = window_start + timedelta(days=1)
    await _seed_incident(
        db_session,
        estate_id=world.estate_a.estate_id,
        created_by=world.hoa_admin_a.user_id,
        occurred_at=inside,
    )
    await _seed_incident(
        db_session,
        estate_id=world.estate_a.estate_id,
        created_by=world.hoa_admin_a.user_id,
        occurred_at=inside,
        status="resolved",
        resolved_at=inside,
    )
    await _seed_incident(
        db_session,
        estate_id=world.estate_b.estate_id,
        created_by=world.hoa_admin_b.user_id,
        occurred_at=inside,
    )
    await _seed_incident(
        db_session,
        estate_id=world.estate_a.estate_id,
        created_by=world.hoa_admin_a.user_id,
        occurred_at=window_start - timedelta(days=1),
    )

    repository = SecurityIncidentRepository(db_session)
    estate_a = await repository.count_in_window(
        estate_id=world.estate_a.estate_id, start=window_start, end=window_end
    )
    estate_b = await repository.count_in_window(
        estate_id=world.estate_b.estate_id, start=window_start, end=window_end
    )

    assert estate_a == 2  # both statuses count, the out-of-window row does not
    assert estate_b == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_patch_cannot_move_an_incident_to_another_estate(db_session, async_client) -> None:
    from tests.factories import build_two_estate_world

    world = await build_two_estate_world(db_session)
    incident = await _seed_incident(
        db_session, estate_id=world.estate_a.estate_id, created_by=world.hoa_admin_a.user_id
    )

    response = await async_client.patch(
        f"{COLLECTION_PATH}/{incident.incident_id}?estate_id={world.estate_a.estate_id}",
        json={"severity": "low", "estate_id": world.estate_b.estate_id},
        headers=_bearer(world.hoa_admin_a),
    )

    # estate_id is not part of the patch contract at all
    assert response.status_code == 422
    await db_session.refresh(incident)
    assert incident.estate_id == world.estate_a.estate_id
