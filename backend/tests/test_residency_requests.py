"""Residency requests: the admin-approval path onto an estate.

Three layers, following the project's conventions:

* **policy / DTO / service unit tests** run everywhere without a database. They pin
  the vocabulary, the DTO bounds, submit/approve/reject rules, self-approval being
  impossible, the single commit, and that a failing email never fails the request.
* **route guards** prove who may call what from inside the real router, and that no
  decision is reachable by editing a status field.
* **integration tests** (``@pytest.mark.integration``) carry every claim that needs
  persisted rows: the full reset-submit-approve journey, the 409 on a second
  decision, and that a rejection grants nothing. They auto-skip when
  ``TEST_DATABASE_URL`` is unset.
"""
from __future__ import annotations

import asyncio
import io
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from tests.operator_fixtures import signup_fixture
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.router import create_api_router
from app.common.enums import ResidencyRequestStatus, UserRole
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.db.session import get_db
from app.identity.api.dependencies import get_current_user
from app.identity.schemas.residency_request import (
    PendingResidencyCountResponse,
    ResidencyRequestCreate,
    ResidencyRequestReject,
    ResidencyRequestResponse,
)
from app.notifications.email import EmailMessage, NullEmailSender
from app.notifications.residency_notifications import ResidencyNotifier


# --------------------------------------------------------------------------- #
# 1. Vocabulary and DTOs
# --------------------------------------------------------------------------- #
def test_status_vocabulary_is_exactly_the_three_values_the_database_allows() -> None:
    assert [status.value for status in ResidencyRequestStatus] == [
        "pending",
        "approved",
        "rejected",
    ]


def test_create_dto_strips_whitespace_and_forbids_extra_fields() -> None:
    payload = ResidencyRequestCreate.model_validate(
        {"estate_id": 4, "unit_no": " a-1 ", "note": "  moved in last week  "}
    )
    assert payload.unit_no == "a-1"
    assert payload.note == "moved in last week"

    with pytest.raises(ValidationError):
        ResidencyRequestCreate.model_validate({"estate_id": 4, "unit_no": "A-1", "status": "approved"})
    with pytest.raises(ValidationError):
        ResidencyRequestCreate.model_validate({"estate_id": 0, "unit_no": "A-1"})
    with pytest.raises(ValidationError):
        ResidencyRequestCreate.model_validate({"estate_id": 4, "unit_no": ""})
    with pytest.raises(ValidationError):
        ResidencyRequestCreate.model_validate({"estate_id": 4, "unit_no": "X" * 11})


def test_create_dto_accepts_estate_access_without_a_unit_number() -> None:
    payload = ResidencyRequestCreate.model_validate(
        {"estate_id": 4, "note": "Please confirm my residency."}
    )
    assert payload.estate_id == 4
    assert payload.unit_no is None
    assert payload.note == "Please confirm my residency."


def test_reject_dto_only_carries_a_note_and_forbids_a_status() -> None:
    assert ResidencyRequestReject.model_validate({}).note is None
    assert ResidencyRequestReject.model_validate({"note": " not on the lease "}).note == "not on the lease"
    # A client must not be able to smuggle a decision in via the reject body.
    with pytest.raises(ValidationError):
        ResidencyRequestReject.model_validate({"status": "approved"})
    with pytest.raises(ValidationError):
        ResidencyRequestReject.model_validate({"note": "x" * 501})


# --------------------------------------------------------------------------- #
# 2. Fakes
# --------------------------------------------------------------------------- #
class FakeSession:
    def __init__(self, *, explode_on_commit: bool = False) -> None:
        self.commits = 0
        self.rollbacks = 0
        self._explode = explode_on_commit

    async def commit(self) -> None:
        if self._explode:
            from sqlalchemy.exc import IntegrityError

            raise IntegrityError("stmt", {}, Exception("duplicate key value"))
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def refresh(self, _row) -> None:
        return None


def _request_row(**overrides):
    row = {
        "request_id": 31,
        "estate_id": 4,
        "user_id": 8,
        "property_id": 21,
        "unit_no": "A-1",
        "status": ResidencyRequestStatus.pending.value,
        "applicant_name": "Nandi Dlamini",
        "applicant_email": "nandi@example.com",
        "applicant_phone": "082 000 0000",
        "note": None,
        "decided_by": None,
        "decided_at": None,
        "decision_note": None,
        "notified_at": None,
        "decision_notified_at": None,
        "created_at": datetime(2026, 10, 13, 9, 30, tzinfo=timezone.utc),
    }
    row.update(overrides)
    return SimpleNamespace(**row)


class FakeRequestRepo:
    def __init__(
        self,
        *,
        pending=None,
        by_id=None,
        rows=None,
        total=None,
        pending_count=0,
        owner_rows=None,
    ) -> None:
        self._pending = pending
        self._by_id = by_id
        self._rows = rows or []
        self._total = total if total is not None else len(self._rows)
        self._pending_count = pending_count
        self._owner_rows = owner_rows or []
        self.added: dict | None = None
        self.saved: list = []
        self.lock_calls: list[bool] = []
        self.list_args: dict | None = None

    async def add(self, **fields):
        self.added = fields
        return _request_row(**fields)

    async def save(self, row):
        self.saved.append(row)
        return row

    async def get_by_id_in_estate(self, *, request_id, estate_id, for_update=False):
        self.lock_calls.append(for_update)
        if self._by_id is not None and self._by_id.estate_id == estate_id:
            return self._by_id
        return None

    async def get_pending_for_user_and_estate(self, *, user_id, estate_id):
        return self._pending

    async def list_for_estate(self, *, estate_id, status=None, search=None, offset=0, limit=100):
        self.list_args = {
            "estate_id": estate_id,
            "status": status,
            "search": search,
            "offset": offset,
            "limit": limit,
        }
        return list(self._rows)

    async def count_for_estate(self, *, estate_id, status=None, search=None):
        return self._total

    async def count_pending_for_estate(self, *, estate_id):
        return self._pending_count

    async def list_for_user(self, *, user_id):
        return list(self._owner_rows)


class FakeMembershipRepo:
    def __init__(self, *, existing=None, contacts=(), explode: bool = False) -> None:
        self._existing = existing
        self._contacts = contacts
        self.added: list[dict] = []
        self._explode = explode

    async def get_for_user_and_estate(self, *, user_id, estate_id):
        return self._existing

    async def add(self, **fields):
        if self._explode:
            raise AssertionError("no membership may be created")
        self.added.append(fields)
        return SimpleNamespace(membership_id=len(self.added), **fields)

    async def list_contacts_for_role(self, *, estate_id, membership_role):
        return list(self._contacts)


class FakeEventRepo:
    def __init__(self) -> None:
        self.records: list[dict] = []

    async def record(self, **fields):
        self.records.append(fields)
        return SimpleNamespace(event_id=len(self.records), **fields)


class FakeEstateRepo:
    def __init__(self, *, estate=None, many=None) -> None:
        self._estate = estate
        self._many = many or {}

    async def get_by_id(self, estate_id):
        return self._estate

    async def get_many_by_ids(self, estate_ids):
        return {estate_id: estate for estate_id, estate in self._many.items() if estate_id in estate_ids}


class FakePropertyRepo:
    def __init__(self, unit) -> None:
        self._unit = unit
        self.lookups: list[tuple[int, str]] = []

    async def get_by_unit_no_in_estate_ci(self, *, estate_id, unit_no):
        self.lookups.append((estate_id, unit_no))
        return self._unit


class FakeAuthz:
    def __init__(self, *, allowed_estate_ids=()) -> None:
        self.allowed = set(allowed_estate_ids)
        self.calls: list[int] = []

    async def require_role(self, *, actor, estate_id, allowed_roles):
        self.calls.append(estate_id)
        if actor.role not in allowed_roles or estate_id not in self.allowed:
            raise ForbiddenException("Your estate membership does not permit this action.")
        return SimpleNamespace(estate_id=estate_id, is_estate_admin=True)


class FakeNotifier:
    def __init__(self, *, creation_result=True, decision_result=True) -> None:
        self.creation_result = creation_result
        self.decision_result = decision_result
        self.creation_calls: list[dict] = []
        self.decision_calls: list[dict] = []

    async def notify_new_request(self, *, estate_name, request):
        self.creation_calls.append({"estate_name": estate_name, "request": request})
        return self.creation_result

    async def notify_decision(self, *, estate_name, request):
        self.decision_calls.append({"estate_name": estate_name, "request": request})
        return self.decision_result


def _service(
    monkeypatch,
    *,
    requests=None,
    memberships=None,
    events=None,
    estates=None,
    properties=None,
    authz=None,
    notifier=None,
    session=None,
    limiter=None,
):
    import app.identity.services.residency_request_service as module

    monkeypatch.setattr(module, "EstateResidencyRequestRepository", lambda _db: requests)
    monkeypatch.setattr(module, "EstateMembershipRepository", lambda _db: memberships)
    monkeypatch.setattr(module, "EstateMembershipEventRepository", lambda _db: events)
    monkeypatch.setattr(module, "EstateRepository", lambda _db: estates)
    monkeypatch.setattr(module, "PropertyRepository", lambda _db: properties)
    monkeypatch.setattr(module, "EstateAuthorizationService", lambda _db: authz)
    return module.ResidencyRequestService(
        session or FakeSession(),
        notifier=notifier or FakeNotifier(),
        limiter=limiter,
    )


def _resident(user_id: int = 8):
    return SimpleNamespace(
        user_id=user_id,
        role=UserRole.resident.value,
        full_name="Nandi Dlamini",
        email="nandi@example.com",
        phoneno="082 000 0000",
    )


def _admin(user_id: int = 3):
    return SimpleNamespace(user_id=user_id, role=UserRole.hoa_admin.value)


def _unit(**overrides):
    row = {"unit_id": 21, "estate_id": 4, "unit_no": "A-1"}
    row.update(overrides)
    return SimpleNamespace(**row)


def _estate(**overrides):
    row = {"estate_id": 4, "name": "Zambezi Country Estate"}
    row.update(overrides)
    return SimpleNamespace(**row)


# --------------------------------------------------------------------------- #
# 3. Submit: what a resident may do, and what it never grants
# --------------------------------------------------------------------------- #
def test_submit_records_a_pending_request_and_creates_no_membership(monkeypatch) -> None:
    session = FakeSession()
    requests = FakeRequestRepo()
    memberships = FakeMembershipRepo()
    notifier = FakeNotifier()
    service = _service(
        monkeypatch,
        requests=requests,
        memberships=memberships,
        events=FakeEventRepo(),
        estates=FakeEstateRepo(estate=_estate()),
        properties=FakePropertyRepo(_unit()),
        notifier=notifier,
        session=session,
    )

    result = asyncio.run(
        service.submit(_resident(), ResidencyRequestCreate(estate_id=4, unit_no=" a-1 "))
    )

    assert requests.added is not None
    assert requests.added["status"] == ResidencyRequestStatus.pending.value
    assert requests.added["estate_id"] == 4
    assert requests.added["property_id"] == 21
    assert requests.added["unit_no"] == "A-1"
    assert requests.added["applicant_name"] == "Nandi Dlamini"
    assert requests.added["applicant_email"] == "nandi@example.com"
    assert requests.added["applicant_phone"] == "082 000 0000"
    # Submitting grants nothing.
    assert memberships.added == []
    assert result.status == ResidencyRequestStatus.pending.value
    assert result.estate_name == "Zambezi Country Estate"
    # One commit for the business state, plus one for the notification stamp.
    assert notifier.creation_calls and notifier.creation_calls[0]["estate_name"] == "Zambezi Country Estate"
    assert session.commits == 2


def test_submit_without_unit_records_pending_estate_access_request(monkeypatch) -> None:
    requests = FakeRequestRepo()
    service = _service(
        monkeypatch,
        requests=requests,
        memberships=FakeMembershipRepo(),
        events=FakeEventRepo(),
        estates=FakeEstateRepo(estate=_estate()),
        properties=FakePropertyRepo(None),
    )

    result = asyncio.run(service.submit(_resident(), ResidencyRequestCreate(estate_id=4)))

    assert requests.added is not None
    assert requests.added["property_id"] is None
    assert requests.added["unit_no"] is None
    assert result.status == ResidencyRequestStatus.pending.value
    assert result.unit_no is None


def test_submit_unknown_estate_is_a_404_and_is_rate_limited(monkeypatch) -> None:
    from app.identity.services.join_attempt_limiter import JoinAttemptLimiter

    limiter = JoinAttemptLimiter()
    requests = FakeRequestRepo()
    service = _service(
        monkeypatch,
        requests=requests,
        memberships=FakeMembershipRepo(),
        events=FakeEventRepo(),
        estates=FakeEstateRepo(estate=None),
        properties=FakePropertyRepo(_unit()),
        limiter=limiter,
    )

    with pytest.raises(NotFoundException):
        asyncio.run(service.submit(_resident(), ResidencyRequestCreate(estate_id=99, unit_no="A-1")))
    assert requests.added is None
    assert limiter.failures_in_window(8) == 1


def test_submit_unknown_unit_is_a_404_and_counts_against_the_limiter(monkeypatch) -> None:
    from app.identity.services.join_attempt_limiter import JoinAttemptLimiter

    limiter = JoinAttemptLimiter()
    requests = FakeRequestRepo()
    service = _service(
        monkeypatch,
        requests=requests,
        memberships=FakeMembershipRepo(),
        events=FakeEventRepo(),
        estates=FakeEstateRepo(estate=_estate()),
        properties=FakePropertyRepo(None),
        limiter=limiter,
    )

    with pytest.raises(NotFoundException):
        asyncio.run(service.submit(_resident(), ResidencyRequestCreate(estate_id=4, unit_no="Z-9")))
    assert requests.added is None
    assert limiter.failures_in_window(8) == 1


def test_submit_is_a_409_when_the_resident_is_already_a_member(monkeypatch) -> None:
    session = FakeSession()
    requests = FakeRequestRepo()
    service = _service(
        monkeypatch,
        requests=requests,
        memberships=FakeMembershipRepo(existing=SimpleNamespace(membership_id=1)),
        events=FakeEventRepo(),
        estates=FakeEstateRepo(estate=_estate()),
        properties=FakePropertyRepo(_unit()),
        session=session,
    )

    with pytest.raises(ConflictException):
        asyncio.run(service.submit(_resident(), ResidencyRequestCreate(estate_id=4, unit_no="A-1")))
    assert requests.added is None
    assert session.commits == 0


def test_submit_is_a_409_when_one_is_already_pending(monkeypatch) -> None:
    session = FakeSession()
    requests = FakeRequestRepo(pending=_request_row())
    service = _service(
        monkeypatch,
        requests=requests,
        memberships=FakeMembershipRepo(),
        events=FakeEventRepo(),
        estates=FakeEstateRepo(estate=_estate()),
        properties=FakePropertyRepo(_unit()),
        session=session,
    )

    with pytest.raises(ConflictException):
        asyncio.run(service.submit(_resident(), ResidencyRequestCreate(estate_id=4, unit_no="A-1")))
    assert requests.added is None
    assert session.commits == 0


def test_submit_survives_a_concurrent_duplicate_as_a_409(monkeypatch) -> None:
    session = FakeSession(explode_on_commit=True)
    service = _service(
        monkeypatch,
        requests=FakeRequestRepo(),
        memberships=FakeMembershipRepo(),
        events=FakeEventRepo(),
        estates=FakeEstateRepo(estate=_estate()),
        properties=FakePropertyRepo(_unit()),
        session=session,
    )

    with pytest.raises(ConflictException):
        asyncio.run(service.submit(_resident(), ResidencyRequestCreate(estate_id=4, unit_no="A-1")))
    assert session.rollbacks == 1


def test_a_failing_notification_never_fails_the_request(monkeypatch) -> None:
    session = FakeSession()
    requests = FakeRequestRepo()
    notifier = FakeNotifier(creation_result=False)
    service = _service(
        monkeypatch,
        requests=requests,
        memberships=FakeMembershipRepo(),
        events=FakeEventRepo(),
        estates=FakeEstateRepo(estate=_estate()),
        properties=FakePropertyRepo(_unit()),
        notifier=notifier,
        session=session,
    )

    result = asyncio.run(
        service.submit(_resident(), ResidencyRequestCreate(estate_id=4, unit_no="A-1"))
    )

    # The request is committed and pending; only the notification stamp is absent.
    assert requests.added["status"] == ResidencyRequestStatus.pending.value
    assert result.status == ResidencyRequestStatus.pending.value
    assert requests.saved == []
    assert session.commits == 1
    assert notifier.creation_calls  # it was attempted


# --------------------------------------------------------------------------- #
# 4. Approve: the only path that grants access
# --------------------------------------------------------------------------- #
def _approve_service(
    monkeypatch,
    *,
    request=None,
    memberships=None,
    events=None,
    session=None,
    authz=None,
    notifier=None,
):
    return _service(
        monkeypatch,
        requests=FakeRequestRepo(by_id=request or _request_row()),
        memberships=memberships or FakeMembershipRepo(),
        events=events or FakeEventRepo(),
        estates=FakeEstateRepo(many={4: _estate()}),
        properties=FakePropertyRepo(_unit()),
        authz=authz or FakeAuthz(allowed_estate_ids={4}),
        notifier=notifier or FakeNotifier(),
        session=session,
    )


def test_approve_creates_the_membership_event_and_stamps_the_decision(monkeypatch) -> None:
    session = FakeSession()
    membership_repo = FakeMembershipRepo()
    events = FakeEventRepo()
    request = _request_row()
    service = _approve_service(
        monkeypatch, request=request, memberships=membership_repo, events=events, session=session
    )

    result = asyncio.run(service.approve(_admin(), estate_id=4, request_id=31))

    assert events.records == [
        {
            "estate_id": 4,
            "user_id": 8,
            "membership_role": UserRole.resident.value,
            "property_id": 21,
            "event_type": "joined",
            "actor_user_id": 3,
        }
    ]
    assert membership_repo.added == [
        {
            "user_id": 8,
            "estate_id": 4,
            "property_id": 21,
            "membership_role": UserRole.resident.value,
        }
    ]
    assert request.status == ResidencyRequestStatus.approved.value
    assert request.decided_by == 3
    assert request.decided_at is not None
    assert result.status == ResidencyRequestStatus.approved.value
    # The row is read with a lock so concurrent decisions cannot both win.
    assert service._requests.lock_calls == [True]


def test_approve_grants_estate_membership_when_no_unit_was_submitted(monkeypatch) -> None:
    membership_repo = FakeMembershipRepo()
    events = FakeEventRepo()
    request = _request_row(property_id=None, unit_no=None)
    service = _approve_service(
        monkeypatch, request=request, memberships=membership_repo, events=events
    )

    result = asyncio.run(service.approve(_admin(), estate_id=4, request_id=31))

    assert membership_repo.added == [
        {
            "user_id": 8,
            "estate_id": 4,
            "property_id": None,
            "membership_role": UserRole.resident.value,
        }
    ]
    assert events.records[0]["property_id"] is None
    assert result.status == ResidencyRequestStatus.approved.value


def test_approve_requires_estate_admin_and_grants_nothing_when_refused(monkeypatch) -> None:
    membership_repo = FakeMembershipRepo(explode=True)
    service = _approve_service(
        monkeypatch,
        memberships=membership_repo,
        authz=FakeAuthz(allowed_estate_ids=set()),
    )

    with pytest.raises(ForbiddenException):
        asyncio.run(service.approve(_admin(), estate_id=4, request_id=31))
    assert membership_repo.added == []


def test_a_resident_cannot_approve_their_own_request(monkeypatch) -> None:
    # Self-approval is impossible: the decider must hold the hoa_admin role *and* a
    # matching membership. A resident actor fails the role check in the service.
    service = _approve_service(monkeypatch, authz=FakeAuthz(allowed_estate_ids={4}))
    with pytest.raises(ForbiddenException):
        asyncio.run(service.approve(_resident(), estate_id=4, request_id=31))


def test_approve_is_a_409_when_the_request_was_already_decided(monkeypatch) -> None:
    request = _request_row(
        status=ResidencyRequestStatus.rejected.value,
        decided_at=datetime(2026, 10, 13, tzinfo=timezone.utc),
    )
    membership_repo = FakeMembershipRepo(explode=True)
    service = _approve_service(monkeypatch, request=request, memberships=membership_repo)

    with pytest.raises(ConflictException):
        asyncio.run(service.approve(_admin(), estate_id=4, request_id=31))
    assert membership_repo.added == []


def test_approve_does_not_duplicate_a_membership_the_resident_already_has(monkeypatch) -> None:
    session = FakeSession()
    request = _request_row()
    membership_repo = FakeMembershipRepo(existing=SimpleNamespace(membership_id=77))
    service = _approve_service(monkeypatch, request=request, memberships=membership_repo, session=session)

    asyncio.run(service.approve(_admin(), estate_id=4, request_id=31))

    assert membership_repo.added == []
    assert request.status == ResidencyRequestStatus.approved.value


def test_approve_refuses_a_request_whose_applicant_account_is_gone(monkeypatch) -> None:
    request = _request_row(user_id=None)
    service = _approve_service(monkeypatch, request=request)

    with pytest.raises(ConflictException):
        asyncio.run(service.approve(_admin(), estate_id=4, request_id=31))


def test_approve_of_a_request_from_another_estate_is_a_404(monkeypatch) -> None:
    service = _approve_service(monkeypatch, request=_request_row(estate_id=99))
    with pytest.raises(NotFoundException):
        asyncio.run(service.approve(_admin(), estate_id=4, request_id=31))


# --------------------------------------------------------------------------- #
# 5. Reject: never grants anything
# --------------------------------------------------------------------------- #
def test_reject_marks_the_request_and_creates_no_membership(monkeypatch) -> None:
    session = FakeSession()
    request = _request_row()
    membership_repo = FakeMembershipRepo(explode=True)
    notifier = FakeNotifier()
    service = _approve_service(
        monkeypatch, request=request, memberships=membership_repo, session=session, notifier=notifier
    )

    result = asyncio.run(service.reject(_admin(), estate_id=4, request_id=31, note="not on the lease"))

    assert membership_repo.added == []
    assert request.status == ResidencyRequestStatus.rejected.value
    assert request.decision_note == "not on the lease"
    assert request.decided_at is not None
    assert result.status == ResidencyRequestStatus.rejected.value
    assert notifier.decision_calls  # the applicant is told


def test_reject_is_a_409_when_already_decided(monkeypatch) -> None:
    request = _request_row(
        status=ResidencyRequestStatus.approved.value,
        decided_at=datetime(2026, 10, 13, tzinfo=timezone.utc),
    )
    service = _approve_service(monkeypatch, request=request)
    with pytest.raises(ConflictException):
        asyncio.run(service.reject(_admin(), estate_id=4, request_id=31))


# --------------------------------------------------------------------------- #
# 6. The admin queue
# --------------------------------------------------------------------------- #
def test_list_for_estate_requires_admin_and_forwards_filters(monkeypatch) -> None:
    rows = [_request_row(request_id=31), _request_row(request_id=30, status="approved")]
    requests = FakeRequestRepo(rows=rows, total=2)
    service = _service(
        monkeypatch,
        requests=requests,
        memberships=FakeMembershipRepo(),
        events=FakeEventRepo(),
        estates=FakeEstateRepo(many={4: _estate()}),
        properties=FakePropertyRepo(_unit()),
        authz=FakeAuthz(allowed_estate_ids={4}),
    )

    page = asyncio.run(
        service.list_for_estate(
            _admin(), estate_id=4, status="pending", search=" nandi ", page=2, page_size=10
        )
    )

    assert requests.list_args == {
        "estate_id": 4,
        "status": "pending",
        "search": " nandi ",
        "offset": 10,
        "limit": 10,
    }
    assert page.total == 2
    assert page.page == 2
    assert page.size == 10
    assert [item.request_id for item in page.items] == [31, 30]


def test_list_for_estate_is_denied_for_a_non_admin(monkeypatch) -> None:
    service = _service(
        monkeypatch,
        requests=FakeRequestRepo(),
        memberships=FakeMembershipRepo(),
        events=FakeEventRepo(),
        estates=FakeEstateRepo(),
        properties=FakePropertyRepo(None),
        authz=FakeAuthz(allowed_estate_ids=set()),
    )
    with pytest.raises(ForbiddenException):
        asyncio.run(
            service.list_for_estate(
                _admin(), estate_id=4, status=None, search=None, page=1, page_size=20
            )
        )


def test_pending_count_requires_admin_and_returns_the_number(monkeypatch) -> None:
    service = _service(
        monkeypatch,
        requests=FakeRequestRepo(pending_count=3),
        memberships=FakeMembershipRepo(),
        events=FakeEventRepo(),
        estates=FakeEstateRepo(many={4: _estate()}),
        properties=FakePropertyRepo(_unit()),
        authz=FakeAuthz(allowed_estate_ids={4}),
    )
    assert asyncio.run(service.pending_count(_admin(), estate_id=4)) == 3


def test_list_mine_returns_only_the_callers_requests(monkeypatch) -> None:
    rows = [_request_row(), _request_row(request_id=20, estate_id=7)]
    service = _service(
        monkeypatch,
        requests=FakeRequestRepo(owner_rows=rows),
        memberships=FakeMembershipRepo(),
        events=FakeEventRepo(),
        estates=FakeEstateRepo(many={4: _estate(), 7: _estate(estate_id=7, name="Other Estate")}),
        properties=FakePropertyRepo(_unit()),
    )

    result = asyncio.run(service.list_mine(_resident()))

    assert [item.request_id for item in result] == [31, 20]
    assert result[1].estate_name == "Other Estate"


# --------------------------------------------------------------------------- #
# 7. The notifier: recipients, content, and graceful failure
# --------------------------------------------------------------------------- #
class RecordingSender:
    def __init__(self, *, explode: bool = False) -> None:
        self.messages: list[EmailMessage] = []
        self._explode = explode

    async def send(self, message: EmailMessage) -> None:
        if self._explode:
            raise RuntimeError("relay down")
        self.messages.append(message)


def _notifier(monkeypatch, *, sender, contacts=()):
    import app.notifications.residency_notifications as module

    monkeypatch.setattr(
        module, "EstateMembershipRepository", lambda _db: FakeMembershipRepo(contacts=contacts)
    )
    return module.ResidencyNotifier(object(), sender=sender, base_url="https://valora.example")


def test_new_request_email_goes_to_the_estates_own_admins_with_no_secrets(monkeypatch) -> None:
    sender = RecordingSender()
    notifier = _notifier(
        monkeypatch,
        sender=sender,
        contacts=[("Ada Admin", "ada@estate.example"), ("Bob Admin", "bob@estate.example")],
    )
    request = _request_row()

    delivered = asyncio.run(
        notifier.notify_new_request(estate_name="Zambezi Country Estate", request=request)
    )

    assert delivered is True
    assert len(sender.messages) == 1
    message = sender.messages[0]
    assert message.to == ("ada@estate.example", "bob@estate.example")
    assert "Zambezi Country Estate" in message.subject
    assert "A-1" in message.body
    assert "Nandi Dlamini" in message.body
    assert "nandi@example.com" in message.body
    # A deep link into the admin queue, and nothing secret.
    assert "request=31" in message.body
    assert message.reply_to == "nandi@example.com"


def test_new_request_email_is_skipped_when_the_estate_has_no_admin_contact(monkeypatch) -> None:
    sender = RecordingSender()
    notifier = _notifier(monkeypatch, sender=sender, contacts=[])

    delivered = asyncio.run(
        notifier.notify_new_request(estate_name="Zambezi Country Estate", request=_request_row())
    )

    assert delivered is False
    assert sender.messages == []


def test_a_dead_relay_is_reported_as_not_delivered_rather_than_raised(monkeypatch) -> None:
    notifier = _notifier(
        monkeypatch, sender=RecordingSender(explode=True), contacts=[("Ada", "ada@estate.example")]
    )
    delivered = asyncio.run(
        notifier.notify_new_request(estate_name="Zambezi Country Estate", request=_request_row())
    )
    assert delivered is False


def test_decision_email_reflects_the_persisted_outcome(monkeypatch) -> None:
    sender = RecordingSender()
    notifier = _notifier(monkeypatch, sender=sender)
    approved = _request_row(
        status=ResidencyRequestStatus.approved.value,
        decided_at=datetime(2026, 10, 13, 10, 0, tzinfo=timezone.utc),
    )
    rejected = _request_row(
        status=ResidencyRequestStatus.rejected.value,
        decision_note="not on the lease",
        decided_at=datetime(2026, 10, 13, 10, 0, tzinfo=timezone.utc),
    )

    assert asyncio.run(notifier.notify_decision(estate_name="Zambezi", request=approved)) is True
    assert asyncio.run(notifier.notify_decision(estate_name="Zambezi", request=rejected)) is True

    assert sender.messages[0].to == ("nandi@example.com",)
    assert "approved" in sender.messages[0].subject.lower()
    assert "not approved" in sender.messages[1].subject.lower()
    assert "not on the lease" in sender.messages[1].body


def test_default_sender_sends_nothing() -> None:
    # EMAIL_ENABLED defaults to false, so the NullEmailSender is the real default.
    asyncio.run(NullEmailSender().send(EmailMessage(to=("x@example.com",), subject="hi", body="body")))


def test_email_message_refuses_header_injection() -> None:
    with pytest.raises(ValueError):
        EmailMessage(to=("x@example.com",), subject="ok\nBcc: evil@example.com", body="body")
    with pytest.raises(ValueError):
        EmailMessage(to=("x@example.com\r\nBcc: evil@example.com",), subject="ok", body="body")
    with pytest.raises(ValueError):
        EmailMessage(to=(), subject="ok", body="body")


# --------------------------------------------------------------------------- #
# 8. Route guards
# --------------------------------------------------------------------------- #
def _route_client(*, role: str | None):
    test_app = FastAPI()
    test_app.include_router(create_api_router(True))
    test_app.dependency_overrides[get_db] = lambda: object()
    if role is not None:
        test_app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            user_id=7, role=role
        )
    return TestClient(test_app)


def _paths() -> set[str]:
    app = FastAPI()
    app.include_router(create_api_router(True))
    return set(app.openapi()["paths"])


def test_residency_routes_exist_and_take_no_estate_in_the_path() -> None:
    paths = _paths()
    assert "/api/v1/residency-requests" in paths
    assert "/api/v1/residency-requests/mine" in paths
    assert "/api/v1/residency-requests/pending-count" in paths
    assert "/api/v1/residency-requests/{request_id}/approve" in paths
    assert "/api/v1/residency-requests/{request_id}/reject" in paths
    assert not any("estate" in path for path in paths if "/residency-requests" in path)


def test_residency_endpoints_require_authentication() -> None:
    anonymous = _route_client(role=None)
    assert anonymous.get("/api/v1/residency-requests/mine").status_code == 401
    assert anonymous.post(
        "/api/v1/residency-requests", json={"estate_id": 1, "unit_no": "A-1"}
    ).status_code == 401
    assert anonymous.get("/api/v1/residency-requests?estate_id=1").status_code == 401
    assert anonymous.get("/api/v1/residency-requests/pending-count?estate_id=1").status_code == 401
    assert anonymous.post("/api/v1/residency-requests/1/approve?estate_id=1").status_code == 401
    assert anonymous.post("/api/v1/residency-requests/1/reject?estate_id=1", json={}).status_code == 401


def test_the_queue_and_decisions_are_administrator_only() -> None:
    resident = _route_client(role="resident")
    assert resident.get("/api/v1/residency-requests?estate_id=1").status_code == 403
    assert resident.get("/api/v1/residency-requests/pending-count?estate_id=1").status_code == 403
    assert resident.post("/api/v1/residency-requests/1/approve?estate_id=1").status_code == 403
    assert resident.post("/api/v1/residency-requests/1/reject?estate_id=1", json={}).status_code == 403


def test_submitting_is_resident_only_at_the_route() -> None:
    for role in ("hoa_admin", "service_provider", "estate_agent", "platform_admin"):
        response = _route_client(role=role).post(
            "/api/v1/residency-requests", json={"estate_id": 1, "unit_no": "A-1"}
        )
        assert response.status_code == 403, (role, response.text)


def test_submit_rejects_a_status_field_in_the_body() -> None:
    response = _route_client(role="resident").post(
        "/api/v1/residency-requests",
        json={"estate_id": 1, "unit_no": "A-1", "status": "approved"},
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# 9. The migration: additive, offline-safe, with a documented downgrade
# --------------------------------------------------------------------------- #
def _offline_sql(direction: str) -> str:
    from alembic import command
    from alembic.config import Config
    import pathlib

    backend_dir = pathlib.Path(__file__).resolve().parent.parent
    cfg = Config(str(backend_dir / "alembic.ini"))
    buffer = io.StringIO()
    cfg.stdout = buffer
    cfg.output_buffer = buffer
    if direction == "up":
        # Scoped to this revision only, so the assertion below is about what *this*
        # migration does and not about the whole replayable history.
        command.upgrade(cfg, "c3f7a1b9d4e2:e7a1b3c5d9f2", sql=True)
    else:
        command.downgrade(cfg, "e7a1b3c5d9f2:c3f7a1b9d4e2", sql=True)
    return buffer.getvalue()


def test_migration_creates_the_table_constraints_and_indexes() -> None:
    sql = _offline_sql("up")
    assert "CREATE TABLE estate_residency_requests" in sql
    assert "fk_estate_residency_requests_estate_id_estates" in sql
    assert "ck_estate_residency_requests_status" in sql
    assert "ck_estate_residency_requests_decided_at_present" in sql
    assert "uq_estate_residency_requests_one_pending_per_user_estate" in sql
    assert "ix_estate_residency_requests_estate_id_status_created_at" in sql


def test_migration_is_additive_and_does_not_touch_the_join_code_path() -> None:
    up = _offline_sql("up")
    down = _offline_sql("down")
    assert "CREATE TABLE estate_join_codes" not in up
    assert "DROP TABLE estate_join_codes" not in down
    assert "DROP TABLE estate_memberships" not in down
    # The downgrade drops exactly what the upgrade added.
    assert "DROP TABLE estate_residency_requests" in down


def test_migration_declares_a_single_new_head_on_the_previous_head() -> None:
    import importlib.util
    import pathlib

    path = (
        pathlib.Path(__file__).resolve().parent.parent
        / "alembic"
        / "versions"
        / "e7a1b3c5d9f2_add_estate_residency_requests.py"
    )
    spec = importlib.util.spec_from_file_location("residency_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "e7a1b3c5d9f2"
    assert module.down_revision == "c3f7a1b9d4e2"
    assert callable(module.upgrade)
    assert callable(module.downgrade)


# --------------------------------------------------------------------------- #
# 10. Integration: real database only. Auto-skip without TEST_DATABASE_URL.
# --------------------------------------------------------------------------- #
PASSWORD = "correct-horse-battery-staple"
BASE = "/api/v1"


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _estate_with_unit(client, *, name: str, email: str, unit_no: str) -> tuple[dict, int, int]:
    registration = await signup_fixture(client,
        f"{BASE}/auth/register",
        json={
            "full_name": "Estate Admin",
            "email": email,
            "password": PASSWORD,
            "account_type": "estate_admin",
            "estate": {
                "name": name,
                "suburb": "Centurion",
                "city": "Pretoria",
                "province": "Gauteng",
            },
        },
    )
    assert registration.status_code == 201, registration.text
    admin_headers = _bearer(registration.json()["access_token"])
    estates = await client.get(f"{BASE}/auth/estates", headers=admin_headers)
    estate_id = estates.json()["estates"][0]["estate_id"]
    units = await client.post(
        f"{BASE}/properties/bulk?estate_id={estate_id}",
        json={"units": [{"unit_no": unit_no, "street_address": f"{unit_no} Ridge Close"}]},
        headers=admin_headers,
    )
    assert units.status_code == 201, units.text
    return admin_headers, estate_id, units.json()[0]["id"]


async def _resident_headers(client, *, email: str) -> dict:
    registered = await signup_fixture(client,
        f"{BASE}/auth/register",
        json={"full_name": "Nandi Dlamini", "email": email, "password": PASSWORD},
    )
    assert registered.status_code == 201, registered.text
    return _bearer(registered.json()["access_token"])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_residency_request_journey_is_approved_into_a_membership(db_session, async_client) -> None:
    from app.identity.repositories.estate_membership_event_repository import (
        EstateMembershipEventRepository,
    )

    admin_headers, estate_id, unit_id = await _estate_with_unit(
        async_client, name="Residency Journey Estate", email="rr_admin@example.com", unit_no="A-1"
    )
    resident_headers = await _resident_headers(async_client, email="rr_resident@example.com")

    # 1. The resident submits; nothing is granted yet.
    submitted = await async_client.post(
        f"{BASE}/residency-requests",
        json={"estate_id": estate_id, "unit_no": " a-1 ", "note": "Lease starts 1 Nov"},
        headers=resident_headers,
    )
    assert submitted.status_code == 201, submitted.text
    body = submitted.json()
    assert body["status"] == "pending"
    assert body["unit_no"] == "A-1"
    request_id = body["request_id"]

    estates = await async_client.get(f"{BASE}/auth/estates", headers=resident_headers)
    assert estates.json()["estates"] == []

    # 2. A duplicate submission while pending is a 409.
    duplicate = await async_client.post(
        f"{BASE}/residency-requests",
        json={"estate_id": estate_id, "unit_no": "A-1"},
        headers=resident_headers,
    )
    assert duplicate.status_code == 409, duplicate.text

    # 3. The admin sees it in the queue and the count.
    count = await async_client.get(
        f"{BASE}/residency-requests/pending-count?estate_id={estate_id}", headers=admin_headers
    )
    assert count.json() == {"pending": 1}
    queue = await async_client.get(
        f"{BASE}/residency-requests?estate_id={estate_id}&status=pending&search=nandi",
        headers=admin_headers,
    )
    assert queue.status_code == 200, queue.text
    assert queue.json()["total"] == 1
    assert queue.json()["items"][0]["applicant_email"] == "rr_resident@example.com"

    # 4. A resident cannot read the queue or decide anything.
    assert (
        await async_client.get(
            f"{BASE}/residency-requests?estate_id={estate_id}", headers=resident_headers
        )
    ).status_code == 403
    assert (
        await async_client.post(
            f"{BASE}/residency-requests/{request_id}/approve?estate_id={estate_id}",
            headers=resident_headers,
        )
    ).status_code == 403

    # 5. Approve: the membership and its event appear, in one decision.
    approved = await async_client.post(
        f"{BASE}/residency-requests/{request_id}/approve?estate_id={estate_id}",
        headers=admin_headers,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["decided_at"] is not None

    estates = await async_client.get(f"{BASE}/auth/estates", headers=resident_headers)
    assert [e["estate_name"] for e in estates.json()["estates"]] == ["Residency Journey Estate"]
    assert estates.json()["estates"][0]["property_ids"] == [unit_id]

    events = await EstateMembershipEventRepository(db_session).list_for_estate(estate_id=estate_id)
    assert [e.event_type for e in events] == ["joined"]
    assert events[0].actor_user_id is not None  # the deciding administrator

    # 6. A second decision is a 409, not an overwrite.
    again = await async_client.post(
        f"{BASE}/residency-requests/{request_id}/approve?estate_id={estate_id}",
        headers=admin_headers,
    )
    assert again.status_code == 409, again.text

    # 7. The status survives a fresh read.
    mine = await async_client.get(f"{BASE}/residency-requests/mine", headers=resident_headers)
    assert [item["status"] for item in mine.json()] == ["approved"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_rejected_request_grants_no_access(db_session, async_client) -> None:
    admin_headers, estate_id, _ = await _estate_with_unit(
        async_client, name="Residency Reject Estate", email="rr_reject_admin@example.com", unit_no="B-1"
    )
    resident_headers = await _resident_headers(async_client, email="rr_reject_resident@example.com")

    submitted = await async_client.post(
        f"{BASE}/residency-requests",
        json={"estate_id": estate_id, "unit_no": "B-1"},
        headers=resident_headers,
    )
    assert submitted.status_code == 201, submitted.text
    request_id = submitted.json()["request_id"]

    rejected = await async_client.post(
        f"{BASE}/residency-requests/{request_id}/reject?estate_id={estate_id}",
        json={"note": "Not on the lease"},
        headers=admin_headers,
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["decision_note"] == "Not on the lease"

    # No membership, no access, and no joined event.
    estates = await async_client.get(f"{BASE}/auth/estates", headers=resident_headers)
    assert estates.json()["estates"] == []
    denied = await async_client.get(
        f"{BASE}/complaints?estate_id={estate_id}", headers=resident_headers
    )
    assert denied.status_code == 403, denied.text

    from app.identity.repositories.estate_membership_event_repository import (
        EstateMembershipEventRepository,
    )

    events = await EstateMembershipEventRepository(db_session).list_for_estate(estate_id=estate_id)
    assert events == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_rejected_resident_may_apply_again(db_session, async_client) -> None:
    admin_headers, estate_id, _ = await _estate_with_unit(
        async_client, name="Residency Retry Estate", email="rr_retry_admin@example.com", unit_no="C-1"
    )
    resident_headers = await _resident_headers(async_client, email="rr_retry_resident@example.com")

    first = await async_client.post(
        f"{BASE}/residency-requests",
        json={"estate_id": estate_id, "unit_no": "C-1"},
        headers=resident_headers,
    )
    await async_client.post(
        f"{BASE}/residency-requests/{first.json()['request_id']}/reject?estate_id={estate_id}",
        json={},
        headers=admin_headers,
    )

    # The partial unique index only forbids two *pending* rows, so a fresh attempt
    # after a rejection succeeds.
    second = await async_client.post(
        f"{BASE}/residency-requests",
        json={"estate_id": estate_id, "unit_no": "C-1"},
        headers=resident_headers,
    )
    assert second.status_code == 201, second.text
    assert second.json()["status"] == "pending"
    assert second.json()["request_id"] != first.json()["request_id"]
