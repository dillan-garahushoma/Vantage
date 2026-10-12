"""BATCH 6A — estate scoping for announcements.

Two layers, deliberately:

* **Policy and query-shape tests** run everywhere, without a database. They pin the
  expiry rule, the estate id the service hands the repository, the request DTOs, and
  the WHERE clause the repository generates — the last one by *executing* that exact
  clause against a real in-memory SQLite table, which is what proves a legacy
  NULL-estate row cannot match an estate-scoped query.
* **Integration tests** (``@pytest.mark.integration``) carry every *isolation* claim.
  The testing skill is explicit that a fake built with ``Class.__new__`` cannot prove
  tenant isolation, so "a member of estate A cannot read estate B" is asserted only
  against a real database. They auto-skip when ``TEST_DATABASE_URL`` is unset, and the
  harness refuses a database whose name does not contain ``test``.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import sqlite

from app.common.enums import UserRole
from app.common.pagination import Page
from app.community.repositories.announcement_repository import AnnouncementRepository
from app.community.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementResponse,
    AnnouncementUpdate,
)
from app.community.services.announcement_service import AnnouncementService
from app.core.exceptions import NotFoundException
from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.identity.api.dependencies import get_current_user
from app.identity.models.user import User
from app.identity.repositories.estate_membership_repository import EstateMembershipRepository
from app.identity.repositories.user_repository import UserRepository
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.main import app

client = TestClient(app)


# --------------------------------------------------------------------------- #
# Test doubles. These prove *policy* and *query shape* only - never isolation.
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
    """Captures the statements a repository builds, returning empty results."""

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


class RecordingAnnouncementRepo:
    """Records what the service asks for, and refuses the unscoped getter."""

    def __init__(self, *, items: list | None = None, total: int = 0, by_id=None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._items = items or []
        self._total = total
        self._by_id = by_id

    async def search(self, **kwargs):
        self.calls.append(("search", kwargs))
        return self._items

    async def count(self, **kwargs):
        self.calls.append(("count", kwargs))
        return self._total

    async def get_by_id_in_estate(self, **kwargs):
        self.calls.append(("get_by_id_in_estate", kwargs))
        return self._by_id

    async def get_by_id(self, *args, **kwargs):
        raise AssertionError("an estate-scoped route must never use the unscoped getter")

    async def create(self, **kwargs):
        self.calls.append(("create", kwargs))
        return SimpleNamespace(
            announcement_id=101,
            created_at=None,
            updated_at=None,
            **kwargs,
        )

    async def save(self, announcement):
        self.calls.append(("save", {}))
        return announcement

    async def delete(self, announcement):
        self.calls.append(("delete", {}))

    def kwargs_for(self, method: str) -> dict:
        return next(kwargs for name, kwargs in self.calls if name == method)


def _service(repo: RecordingAnnouncementRepo, memberships: list) -> AnnouncementService:
    service = AnnouncementService.__new__(AnnouncementService)
    service._repo = repo
    service._estate_authorization = _auth_service(memberships)
    return service


def _announcement(*, estate_id: int, expires_at: datetime | None = None):
    return SimpleNamespace(
        announcement_id=55,
        estate_id=estate_id,
        title="Water shutdown",
        message="Water will be off on Tuesday.",
        created_by=7,
        expires_at=expires_at,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
    )


def _resident(estate_id: int, user_id: int = 21):
    return (
        SimpleNamespace(user_id=user_id, role=UserRole.resident.value),
        [_membership(user_id, estate_id, UserRole.resident.value, property_id=1)],
    )


def _estate_admin(estate_id: int, user_id: int = 22):
    return (
        SimpleNamespace(user_id=user_id, role=UserRole.hoa_admin.value),
        [_membership(user_id, estate_id, UserRole.hoa_admin.value)],
    )


# --------------------------------------------------------------------------- #
# Policy: which estate the service resolves and what it asks the repository for
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_list_scopes_every_repository_call_to_the_requested_estate() -> None:
    repo = RecordingAnnouncementRepo()
    actor, memberships = _resident(estate_id=3)
    service = _service(repo, memberships)

    await service.list_announcements(actor, page=1, size=20, estate_id=3)

    assert [name for name, _ in repo.calls] == ["search", "count"]
    assert repo.kwargs_for("search")["estate_id"] == 3
    assert repo.kwargs_for("count")["estate_id"] == 3


@pytest.mark.asyncio
async def test_include_expired_is_ignored_for_a_non_admin() -> None:
    repo = RecordingAnnouncementRepo()
    actor, memberships = _resident(estate_id=3)

    await _service(repo, memberships).list_announcements(
        actor, page=1, size=20, estate_id=3, include_expired=True
    )

    assert repo.kwargs_for("search")["include_expired"] is False
    assert repo.kwargs_for("count")["include_expired"] is False


@pytest.mark.asyncio
async def test_include_expired_is_honoured_for_an_estate_admin() -> None:
    repo = RecordingAnnouncementRepo()
    actor, memberships = _estate_admin(estate_id=3)

    await _service(repo, memberships).list_announcements(
        actor, page=1, size=20, estate_id=3, include_expired=True
    )

    assert repo.kwargs_for("search")["include_expired"] is True
    assert repo.kwargs_for("count")["include_expired"] is True


@pytest.mark.asyncio
async def test_expired_announcement_is_hidden_from_a_non_admin_on_get() -> None:
    expired = _announcement(estate_id=3, expires_at=datetime.now(timezone.utc) - timedelta(days=1))
    repo = RecordingAnnouncementRepo(by_id=expired)
    actor, memberships = _resident(estate_id=3)

    with pytest.raises(NotFoundException):
        await _service(repo, memberships).get_announcement(55, actor, estate_id=3)


@pytest.mark.asyncio
async def test_expired_announcement_is_visible_to_an_estate_admin_on_get() -> None:
    expired = _announcement(estate_id=3, expires_at=datetime.now(timezone.utc) - timedelta(days=1))
    repo = RecordingAnnouncementRepo(by_id=expired)
    actor, memberships = _estate_admin(estate_id=3)

    response = await _service(repo, memberships).get_announcement(55, actor, estate_id=3)

    assert response.announcement_id == 55


@pytest.mark.asyncio
async def test_get_uses_only_the_estate_scoped_repository_getter() -> None:
    live = _announcement(estate_id=8)
    repo = RecordingAnnouncementRepo(by_id=live)
    actor, memberships = _resident(estate_id=8)

    await _service(repo, memberships).get_announcement(55, actor, estate_id=8)

    assert [name for name, _ in repo.calls] == ["get_by_id_in_estate"]
    assert repo.kwargs_for("get_by_id_in_estate") == {"announcement_id": 55, "estate_id": 8}


@pytest.mark.asyncio
async def test_create_takes_the_estate_from_the_query_and_the_author_from_the_admin() -> None:
    repo = RecordingAnnouncementRepo()
    admin, memberships = _estate_admin(estate_id=9, user_id=44)

    await _service(repo, memberships).create_announcement(
        AnnouncementCreate(title="Water shutdown", message="Off on Tuesday."),
        admin,
        estate_id=9,
    )

    created = repo.kwargs_for("create")
    assert created["estate_id"] == 9
    assert created["created_by"] == 44


@pytest.mark.asyncio
async def test_create_ignores_estate_and_author_supplied_in_the_body() -> None:
    repo = RecordingAnnouncementRepo()
    admin, memberships = _estate_admin(estate_id=9, user_id=44)
    payload = AnnouncementCreate.model_validate(
        {
            "title": "Water shutdown",
            "message": "Off on Tuesday.",
            "estate_id": 999,
            "created_by": 999,
        }
    )

    await _service(repo, memberships).create_announcement(payload, admin, estate_id=9)

    created = repo.kwargs_for("create")
    assert created["estate_id"] == 9
    assert created["created_by"] == 44


@pytest.mark.asyncio
async def test_update_service_cannot_move_an_announcement_to_another_estate() -> None:
    announcement = _announcement(estate_id=8)
    repo = RecordingAnnouncementRepo(by_id=announcement)
    admin, memberships = _estate_admin(estate_id=8)
    payload = AnnouncementUpdate.model_validate({"title": "Renamed", "estate_id": 999})

    await _service(repo, memberships).update_announcement(55, payload, admin, estate_id=8)

    assert announcement.estate_id == 8
    assert announcement.title == "Renamed"
    assert repo.kwargs_for("get_by_id_in_estate")["estate_id"] == 8


def test_announcement_request_dtos_cannot_carry_an_estate_or_an_author() -> None:
    assert set(AnnouncementCreate.model_fields) == {"title", "message", "expires_at"}
    assert set(AnnouncementUpdate.model_fields) == {"title", "message", "expires_at"}

    payload = AnnouncementUpdate.model_validate({"estate_id": 999, "created_by": 999})
    assert payload.model_dump(exclude_unset=True) == {}


# --------------------------------------------------------------------------- #
# Query shape: the estate filter is in the SQL, so a NULL estate cannot match
# --------------------------------------------------------------------------- #
def _announcements_table() -> sqlite3.Connection:
    """A real table with real NULL semantics, holding one legacy estate-less row."""
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE announcements (
            announcement_id INTEGER PRIMARY KEY,
            estate_id INTEGER NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            expires_at TIMESTAMP NULL,
            created_at TIMESTAMP NULL,
            updated_at TIMESTAMP NULL
        )
        """
    )
    connection.execute(
        """
        INSERT INTO announcements VALUES
            (1, 8, 'Estate eight', 'body', 1, NULL, '2026-01-02 00:00:00.000000', NULL),
            (2, 9, 'Estate nine', 'body', 1, NULL, '2026-01-03 00:00:00.000000', NULL),
            (3, NULL, 'Legacy row', 'body', 1, NULL, '2026-01-04 00:00:00.000000', NULL)
        """
    )
    connection.commit()
    return connection


def _compiled(statement) -> str:
    return str(
        statement.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True})
    )


@pytest.mark.asyncio
async def test_search_statement_filters_on_the_estate_column() -> None:
    session = RecordingSession()
    await AnnouncementRepository(session).search(
        offset=0,
        limit=20,
        include_expired=False,
        now=datetime(2026, 2, 1, tzinfo=timezone.utc),
        estate_id=8,
    )

    sql = _compiled(session.statements[0])
    assert "announcements.estate_id = 8" in sql
    assert "announcements.estate_id IS NULL" not in sql


@pytest.mark.asyncio
async def test_search_excludes_legacy_null_estate_rows_when_executed() -> None:
    session = RecordingSession()
    await AnnouncementRepository(session).search(
        offset=0,
        limit=20,
        include_expired=False,
        now=datetime(2026, 2, 1, tzinfo=timezone.utc),
        estate_id=8,
    )

    connection = _announcements_table()
    try:
        rows = connection.execute(_compiled(session.statements[0])).fetchall()
    finally:
        connection.close()

    assert [row[0] for row in rows] == [1]


@pytest.mark.asyncio
async def test_count_excludes_legacy_null_estate_rows_when_executed() -> None:
    session = RecordingSession()
    await AnnouncementRepository(session).count(
        include_expired=True,
        now=datetime(2026, 2, 1, tzinfo=timezone.utc),
        estate_id=8,
    )

    connection = _announcements_table()
    try:
        total = connection.execute(_compiled(session.statements[0])).fetchone()[0]
    finally:
        connection.close()

    assert total == 1


@pytest.mark.asyncio
async def test_scoped_getter_excludes_a_legacy_null_estate_row_when_executed() -> None:
    session = RecordingSession()
    await AnnouncementRepository(session).get_by_id_in_estate(announcement_id=3, estate_id=8)

    connection = _announcements_table()
    try:
        rows = connection.execute(_compiled(session.statements[0])).fetchall()
    finally:
        connection.close()

    # Row 3 exists, but has no estate, so no estate-scoped read may return it.
    assert rows == []


# --------------------------------------------------------------------------- #
# HTTP contract: bounds, role gating, and where the estate comes from
# --------------------------------------------------------------------------- #
def _override(user, *, role: str | None = None) -> dict:
    return {
        get_db: lambda: object(),
        get_current_user: lambda: SimpleNamespace(
            user_id=user.user_id, role=role or user.role
        ),
    }


def _run_with(overrides: dict, action):
    original = app.dependency_overrides.copy()
    app.dependency_overrides.update(overrides)
    try:
        return action()
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)


def test_announcement_list_enforces_pagination_bounds() -> None:
    admin = SimpleNamespace(user_id=1, role=UserRole.hoa_admin.value)

    def action():
        assert client.get("/api/v1/announcements?estate_id=1&page=0").status_code == 422
        assert client.get("/api/v1/announcements?estate_id=1&size=0").status_code == 422
        assert client.get("/api/v1/announcements?estate_id=1&size=101").status_code == 422
        assert client.get("/api/v1/announcements?size=20").status_code == 422
        assert client.get("/api/v1/announcements?estate_id=0").status_code == 422

    _run_with(_override(admin), action)


def test_announcement_list_accepts_the_documented_upper_bound(monkeypatch) -> None:
    admin = SimpleNamespace(user_id=1, role=UserRole.hoa_admin.value)
    monkeypatch.setattr(
        AnnouncementService,
        "list_announcements",
        AsyncMock(return_value=Page[AnnouncementResponse](items=[], total=0, page=1, size=100)),
    )

    def action():
        response = client.get("/api/v1/announcements?estate_id=1&page=1&size=100")
        assert response.status_code == 200, response.text
        assert response.json() == {"items": [], "total": 0, "page": 1, "size": 100, "pages": 0}

    _run_with(_override(admin), action)


def test_resident_cannot_create_update_or_delete_announcements() -> None:
    resident = SimpleNamespace(user_id=5, role=UserRole.resident.value)
    body = {"title": "Water shutdown", "message": "Off on Tuesday."}

    def action():
        assert (
            client.post("/api/v1/announcements?estate_id=1", json=body).status_code == 403
        )
        assert (
            client.patch("/api/v1/announcements/9?estate_id=1", json=body).status_code == 403
        )
        assert client.delete("/api/v1/announcements/9?estate_id=1").status_code == 403

    _run_with(_override(resident), action)


def test_create_route_takes_the_estate_from_the_query_and_the_admin_from_the_token(
    monkeypatch,
) -> None:
    captured: dict = {}

    async def fake_create(self, payload, admin, *, estate_id: int):
        captured["estate_id"] = estate_id
        captured["admin_id"] = admin.user_id
        return AnnouncementResponse(
            announcement_id=1,
            estate_id=estate_id,
            title=payload.title,
            message=payload.message,
            created_by=admin.user_id,
            expires_at=None,
            created_at=None,
            updated_at=None,
        )

    monkeypatch.setattr(AnnouncementService, "create_announcement", fake_create)
    admin = SimpleNamespace(user_id=77, role=UserRole.hoa_admin.value)

    def action():
        response = client.post(
            "/api/v1/announcements?estate_id=2",
            json={
                "title": "Water shutdown",
                "message": "Off on Tuesday.",
                "estate_id": 999,
                "created_by": 999,
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["estate_id"] == 2

    _run_with(_override(admin), action)

    assert captured == {"estate_id": 2, "admin_id": 77}


# --------------------------------------------------------------------------- #
# Isolation: real database only. These auto-skip without TEST_DATABASE_URL.
# --------------------------------------------------------------------------- #
def _bearer(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.user_id)})}"}


async def _seed_announcement(session, *, estate_id, created_by, expires_at=None):
    from app.community.models.announcement import Announcement

    row = Announcement(
        estate_id=estate_id,
        title=f"Announcement for estate {estate_id}",
        message="Body text.",
        created_by=created_by,
        expires_at=expires_at,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


@pytest.mark.integration
@pytest.mark.asyncio
async def test_member_of_estate_a_cannot_list_estate_b_announcements(
    db_session, async_client
) -> None:
    from tests.factories import build_two_estate_world

    world = await build_two_estate_world(db_session)
    await _seed_announcement(
        db_session, estate_id=world.estate_b.estate_id, created_by=world.hoa_admin_b.user_id
    )

    response = await async_client.get(
        f"/api/v1/announcements?estate_id={world.estate_b.estate_id}",
        headers=_bearer(world.resident_a1),
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_estate_a_member_reading_an_estate_b_announcement_gets_404(
    db_session, async_client
) -> None:
    from tests.factories import build_two_estate_world

    world = await build_two_estate_world(db_session)
    foreign = await _seed_announcement(
        db_session, estate_id=world.estate_b.estate_id, created_by=world.hoa_admin_b.user_id
    )

    # The id belongs to estate B, but the request claims estate A, which the user
    # may access: the object is not theirs, so it must look absent.
    response = await async_client.get(
        f"/api/v1/announcements/{foreign.announcement_id}"
        f"?estate_id={world.estate_a.estate_id}",
        headers=_bearer(world.resident_a1),
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_and_get_are_scoped_to_the_estate_they_return(db_session, async_client) -> None:
    from tests.factories import build_two_estate_world

    world = await build_two_estate_world(db_session)
    await _seed_announcement(
        db_session, estate_id=world.estate_a.estate_id, created_by=world.hoa_admin_a.user_id
    )
    await _seed_announcement(
        db_session, estate_id=world.estate_b.estate_id, created_by=world.hoa_admin_b.user_id
    )

    response = await async_client.get(
        f"/api/v1/announcements?estate_id={world.estate_a.estate_id}",
        headers=_bearer(world.resident_a1),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert [item["estate_id"] for item in body["items"]] == [world.estate_a.estate_id]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_hoa_admin_without_estate_membership_cannot_write_announcements(
    db_session, async_client
) -> None:
    from tests.factories import build_two_estate_world

    world = await build_two_estate_world(db_session)
    orphan = await UserRepository(db_session).create(
        full_name="Orphan Admin",
        email="orphan_admin@valora.test",
        password_hash=hash_password("ValidPassword123!"),
        role=UserRole.hoa_admin.value,
    )
    # `UserRepository.create` does not take `hoa_approved`, so the flag is set on
    # the model. It gates no authorisation; this test only needs a global HOA admin.
    orphan.hoa_approved = True
    await db_session.commit()
    target = await _seed_announcement(
        db_session, estate_id=world.estate_a.estate_id, created_by=world.hoa_admin_a.user_id
    )
    headers = _bearer(orphan)
    estate_id = world.estate_a.estate_id

    created = await async_client.post(
        f"/api/v1/announcements?estate_id={estate_id}",
        json={"title": "Not allowed", "message": "Should not be stored."},
        headers=headers,
    )
    updated = await async_client.patch(
        f"/api/v1/announcements/{target.announcement_id}?estate_id={estate_id}",
        json={"title": "Renamed"},
        headers=headers,
    )
    deleted = await async_client.delete(
        f"/api/v1/announcements/{target.announcement_id}?estate_id={estate_id}",
        headers=headers,
    )

    assert [created.status_code, updated.status_code, deleted.status_code] == [403, 403, 403]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_resident_cannot_write_announcements(db_session, async_client) -> None:
    from tests.factories import build_two_estate_world

    world = await build_two_estate_world(db_session)
    target = await _seed_announcement(
        db_session, estate_id=world.estate_a.estate_id, created_by=world.hoa_admin_a.user_id
    )
    headers = _bearer(world.resident_a1)
    estate_id = world.estate_a.estate_id

    created = await async_client.post(
        f"/api/v1/announcements?estate_id={estate_id}",
        json={"title": "Not allowed", "message": "Should not be stored."},
        headers=headers,
    )
    updated = await async_client.patch(
        f"/api/v1/announcements/{target.announcement_id}?estate_id={estate_id}",
        json={"title": "Renamed"},
        headers=headers,
    )
    deleted = await async_client.delete(
        f"/api/v1/announcements/{target.announcement_id}?estate_id={estate_id}",
        headers=headers,
    )

    assert [created.status_code, updated.status_code, deleted.status_code] == [403, 403, 403]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_expired_announcements_are_hidden_from_residents_and_include_expired_is_ignored(
    db_session, async_client
) -> None:
    from tests.factories import build_two_estate_world

    world = await build_two_estate_world(db_session)
    estate_id = world.estate_a.estate_id
    expired = await _seed_announcement(
        db_session,
        estate_id=estate_id,
        created_by=world.hoa_admin_a.user_id,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    headers = _bearer(world.resident_a1)

    listing = await async_client.get(
        f"/api/v1/announcements?estate_id={estate_id}&include_expired=true", headers=headers
    )
    single = await async_client.get(
        f"/api/v1/announcements/{expired.announcement_id}?estate_id={estate_id}",
        headers=headers,
    )

    assert listing.status_code == 200, listing.text
    assert listing.json()["total"] == 0
    assert single.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_estate_admin_can_see_expired_announcements(db_session, async_client) -> None:
    from tests.factories import build_two_estate_world

    world = await build_two_estate_world(db_session)
    estate_id = world.estate_a.estate_id
    expired = await _seed_announcement(
        db_session,
        estate_id=estate_id,
        created_by=world.hoa_admin_a.user_id,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    headers = _bearer(world.hoa_admin_a)

    listing = await async_client.get(
        f"/api/v1/announcements?estate_id={estate_id}&include_expired=true", headers=headers
    )
    single = await async_client.get(
        f"/api/v1/announcements/{expired.announcement_id}?estate_id={estate_id}",
        headers=headers,
    )

    assert listing.status_code == 200, listing.text
    assert listing.json()["total"] == 1
    assert single.status_code == 200, single.text
    assert single.json()["id"] == expired.announcement_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_legacy_null_estate_rows_are_never_returned(db_session, async_client) -> None:
    from app.community.models.announcement import Announcement

    from tests.factories import build_two_estate_world

    world = await build_two_estate_world(db_session)
    legacy = Announcement(
        estate_id=None,
        title="Pre-tenancy announcement",
        message="Belongs to no estate.",
        created_by=world.hoa_admin_a.user_id,
        expires_at=None,
    )
    db_session.add(legacy)
    await db_session.commit()
    await db_session.refresh(legacy)

    listing = await async_client.get(
        f"/api/v1/announcements?estate_id={world.estate_a.estate_id}&include_expired=true",
        headers=_bearer(world.hoa_admin_a),
    )
    single = await async_client.get(
        f"/api/v1/announcements/{legacy.announcement_id}"
        f"?estate_id={world.estate_a.estate_id}",
        headers=_bearer(world.hoa_admin_a),
    )

    assert listing.status_code == 200, listing.text
    assert listing.json()["total"] == 0
    assert single.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_ignores_estate_and_author_in_the_body(db_session, async_client) -> None:
    from tests.factories import build_two_estate_world

    world = await build_two_estate_world(db_session)
    estate_id = world.estate_a.estate_id

    response = await async_client.post(
        f"/api/v1/announcements?estate_id={estate_id}",
        json={
            "title": "Water shutdown",
            "message": "Water will be off on Tuesday.",
            "estate_id": world.estate_b.estate_id,
            "created_by": 999,
        },
        headers=_bearer(world.hoa_admin_a),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["estate_id"] == estate_id
    assert body["created_by"] == world.hoa_admin_a.user_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_http_cannot_move_an_announcement_to_another_estate(
    db_session, async_client
) -> None:
    from tests.factories import build_two_estate_world

    world = await build_two_estate_world(db_session)
    estate_id = world.estate_a.estate_id
    target = await _seed_announcement(
        db_session, estate_id=estate_id, created_by=world.hoa_admin_a.user_id
    )

    response = await async_client.patch(
        f"/api/v1/announcements/{target.announcement_id}?estate_id={estate_id}",
        json={"title": "Renamed", "estate_id": world.estate_b.estate_id},
        headers=_bearer(world.hoa_admin_a),
    )

    assert response.status_code == 200, response.text
    assert response.json()["estate_id"] == estate_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_estate_scoped_list_requires_an_existing_membership(db_session, async_client) -> None:
    from tests.factories import build_two_estate_world

    world = await build_two_estate_world(db_session)
    respites = await EstateMembershipRepository(db_session).list_for_user(
        user_id=world.resident_b1.user_id
    )

    response = await async_client.get(
        f"/api/v1/announcements?estate_id={world.estate_a.estate_id}",
        headers=_bearer(world.resident_b1),
    )

    assert respites
    assert response.status_code == 403
