"""ONB-2 — estate units (bulk), join codes, resident join and member management.

Two layers, following ``test_onb1_role_scoped_signup.py``:

* **Policy / DTO / domain / service tests** run everywhere without a database.
  They pin the join-code alphabet and normalisation, the rate limiter's sliding
  window (with an injected clock), the service rules for joining, listing and
  removing members, the all-or-nothing bulk-unit rule, the append-only shape of
  the event repository, and the offline migration SQL.
* **Integration tests** (``@pytest.mark.integration``) carry every claim that
  needs persisted rows: the full resident journey, cross-estate denial, the
  complaint scoping after a join, the immediate 403 after a removal and the
  concurrent-duplicate join. They auto-skip when ``TEST_DATABASE_URL`` is unset.
"""
from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.router import create_api_router
from app.common.enums import UserRole
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    RateLimitException,
)
from app.db.session import get_db
from app.identity.api.dependencies import get_current_user
from app.identity.domain.join_code import (
    CODE_ALPHABET,
    CODE_LENGTH,
    generate_join_code,
    normalise_join_code,
)
from app.identity.repositories.estate_membership_event_repository import (
    EstateMembershipEventRepository,
)
from app.identity.schemas.join_code import JoinCodeCreateRequest, JoinCodeResponse
from app.identity.schemas.membership import (
    MembershipJoinRequest,
    MembershipJoinResponse,
    MembershipResponse,
)
from app.identity.services.join_attempt_limiter import JoinAttemptLimiter
from app.identity.services.membership_service import MembershipService
from app.property.schemas.property import BulkUnitsRequest
from app.property.services.property_service import PropertyService


# --------------------------------------------------------------------------- #
# 1. Join-code alphabet, generation and normalisation
# --------------------------------------------------------------------------- #
def test_alphabet_excludes_lookalike_characters() -> None:
    # No I/L/O/0/1: a code is read aloud or typed from a screenshot.
    for bad in "ILO01":
        assert bad not in CODE_ALPHABET
    assert len(CODE_ALPHABET) == len(set(CODE_ALPHABET))


def test_join_code_entropy_is_about_49_bits() -> None:
    import math

    bits = CODE_LENGTH * math.log2(len(CODE_ALPHABET))
    assert 48 <= bits <= 52


def test_generated_code_has_the_expected_length_and_alphabet() -> None:
    for _ in range(200):
        code = generate_join_code()
        assert len(code) == CODE_LENGTH
        assert set(code) <= set(CODE_ALPHABET)
        assert code == code.upper()


def test_generated_codes_are_unique_across_many_draws() -> None:
    codes = {generate_join_code() for _ in range(2000)}
    assert len(codes) == 2000


def test_normalisation_trims_upper_cases_and_strips_separators() -> None:
    assert normalise_join_code("  abcd-efgh jk ") == "ABCDEFGHJK"
    assert normalise_join_code("abcd efgh jk") == "ABCDEFGHJK"
    assert normalise_join_code("") == ""
    assert normalise_join_code("   ") == ""
    assert normalise_join_code(None) == ""


# --------------------------------------------------------------------------- #
# 2. Request DTOs: extra=forbid and the documented bounds
# --------------------------------------------------------------------------- #
def test_join_code_request_rejects_extra_fields_and_out_of_range_days() -> None:
    assert JoinCodeCreateRequest.model_validate({}).expires_in_days is None
    assert JoinCodeCreateRequest.model_validate({"expires_in_days": 30}).expires_in_days == 30
    with pytest.raises(ValidationError):
        JoinCodeCreateRequest.model_validate({"estate_id": 1})
    for bad in (0, 366, -1):
        with pytest.raises(ValidationError):
            JoinCodeCreateRequest.model_validate({"expires_in_days": bad})


def test_membership_join_request_rejects_extra_fields_and_requires_both_fields() -> None:
    payload = MembershipJoinRequest.model_validate({"code": " ABCD-EFGHJK ", "unit_no": " A-1 "})
    assert payload.code == "ABCD-EFGHJK"
    assert payload.unit_no == "A-1"
    with pytest.raises(ValidationError):
        MembershipJoinRequest.model_validate({"code": "X", "unit_no": "A-1", "estate_id": 7})
    with pytest.raises(ValidationError):
        MembershipJoinRequest.model_validate({"code": "X"})
    with pytest.raises(ValidationError):
        MembershipJoinRequest.model_validate({"unit_no": "A-1"})
    with pytest.raises(ValidationError):
        MembershipJoinRequest.model_validate({"code": "X", "unit_no": "   "})


def test_bulk_units_request_bounds_and_extra_fields() -> None:
    one = BulkUnitsRequest.model_validate({"units": [{"unit_no": "A-1", "street_address": "1 Road"}]})
    assert len(one.units) == 1

    with pytest.raises(ValidationError):
        BulkUnitsRequest.model_validate({"units": []})
    with pytest.raises(ValidationError):
        BulkUnitsRequest.model_validate(
            {"units": [{"unit_no": f"U{i}", "street_address": "1 Road"} for i in range(501)]}
        )
    # complex_name and suburb are estate-derived, never client-supplied.
    with pytest.raises(ValidationError):
        BulkUnitsRequest.model_validate(
            {
                "units": [
                    {
                        "unit_no": "A-1",
                        "street_address": "1 Road",
                        "complex_name": "Elsewhere",
                    }
                ]
            }
        )
    with pytest.raises(ValidationError):
        BulkUnitsRequest.model_validate(
            {"units": [{"unit_no": "A-1", "street_address": "1 Road", "suburb": "Elsewhere"}]}
        )
    with pytest.raises(ValidationError):
        BulkUnitsRequest.model_validate({"units": [{"unit_no": "A-1", "street_address": "1 Road"}], "estate_id": 1})


# --------------------------------------------------------------------------- #
# 3. The rate limiter: a sliding window with an injectable clock
# --------------------------------------------------------------------------- #
class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_limiter_blocks_after_five_failures_and_recovers_after_the_window() -> None:
    clock = FakeClock()
    limiter = JoinAttemptLimiter(clock=clock)

    assert limiter.failures_in_window(7) == 0
    for _ in range(4):
        limiter.record_failure(7)
    limiter.ensure_allowed(7)  # four failures are still under the limit
    limiter.record_failure(7)
    assert limiter.failures_in_window(7) == 5
    with pytest.raises(RateLimitException):
        limiter.ensure_allowed(7)

    # A different user is unaffected.
    limiter.ensure_allowed(8)

    clock.advance(14 * 60 + 59)
    with pytest.raises(RateLimitException):
        limiter.ensure_allowed(7)

    clock.advance(2)
    limiter.ensure_allowed(7)
    assert limiter.failures_in_window(7) == 0


def test_limiter_window_slides_rather_than_resetting() -> None:
    clock = FakeClock()
    limiter = JoinAttemptLimiter(clock=clock)
    for _ in range(5):
        limiter.record_failure(1)

    clock.advance(601)  # still inside the window
    with pytest.raises(RateLimitException):
        limiter.ensure_allowed(1)
    limiter.record_failure(1)  # a sixth failure, later in the window

    clock.advance(300)  # the original five have now expired, the sixth has not
    limiter.ensure_allowed(1)
    assert limiter.failures_in_window(1) == 1

    clock.advance(900)
    assert limiter.failures_in_window(1) == 0


def test_limiter_can_be_reset_for_one_user() -> None:
    limiter = JoinAttemptLimiter(clock=FakeClock())
    for _ in range(5):
        limiter.record_failure(3)
    limiter.reset(3)
    limiter.ensure_allowed(3)


# --------------------------------------------------------------------------- #
# 4. The event table is append-only
# --------------------------------------------------------------------------- #
def test_event_repository_has_no_update_or_delete_path() -> None:
    assert not hasattr(EstateMembershipEventRepository, "update")
    assert not hasattr(EstateMembershipEventRepository, "delete")
    assert not hasattr(EstateMembershipEventRepository, "remove")
    public = {
        name
        for name in dir(EstateMembershipEventRepository)
        if not name.startswith("_")
    }
    assert public == {"record", "list_for_estate"}


# --------------------------------------------------------------------------- #
# 5. Join-code service: one active code, rotation revokes the previous one
# --------------------------------------------------------------------------- #
def _code_row(**overrides):
    row = {
        "code_id": 1,
        "estate_id": 4,
        "code": "ABCDEFGHJK",
        "created_by": 3,
        "created_at": datetime.now(timezone.utc),
        "expires_at": None,
        "revoked_at": None,
    }
    row.update(overrides)
    return SimpleNamespace(**row)


class FakeCodeRepo:
    def __init__(self, *, unrevoked=None, active=None):
        self._unrevoked = unrevoked
        self._active = active
        self.added: dict | None = None
        self.revoked: list = []
        self.existing_codes: set[str] = set()

    async def get_unrevoked_for_estate(self, estate_id):
        return self._unrevoked

    async def get_active_for_estate(self, *, estate_id, now):
        return self._active

    async def get_by_code(self, code):
        return None

    async def add(self, **fields):
        self.added = fields
        return _code_row(code_id=2, **fields)

    async def revoke(self, row, *, revoked_at):
        self.revoked.append((row, revoked_at))
        row.revoked_at = revoked_at


class FakeAuthz:
    def __init__(self, *, allowed_estate_ids=(), is_admin=True):
        self.allowed = set(allowed_estate_ids)
        self.is_admin = is_admin
        self.calls: list[int] = []

    async def require_role(self, *, actor, estate_id, allowed_roles):
        self.calls.append(estate_id)
        if estate_id not in self.allowed:
            raise ForbiddenException("Your estate membership does not permit this action.")
        return SimpleNamespace(estate_id=estate_id, is_estate_admin=self.is_admin)

    async def resolve_access(self, actor, estate_id):
        self.calls.append(estate_id)
        if estate_id not in self.allowed:
            raise ForbiddenException("You do not have access to this estate.")
        return SimpleNamespace(
            estate_id=estate_id,
            is_estate_admin=self.is_admin,
            membership_roles=frozenset({UserRole.hoa_admin.value}),
            property_ids=frozenset(),
        )

    async def require_membership(self, *, user_id=None, actor=None, estate_id):
        self.calls.append(estate_id)
        if estate_id not in self.allowed:
            raise ForbiddenException("You do not have access to this estate.")
        return SimpleNamespace(estate_id=estate_id, is_estate_admin=self.is_admin)


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def _code_service(monkeypatch, *, repo, authz, session=None):
    import app.identity.services.estate_join_code_service as module

    monkeypatch.setattr(module, "EstateJoinCodeRepository", lambda _db: repo)
    monkeypatch.setattr(module, "EstateAuthorizationService", lambda _db: authz)
    return module.EstateJoinCodeService(session or FakeSession())


def test_rotate_revokes_the_previous_code_and_commits_once(monkeypatch) -> None:
    import asyncio

    previous = _code_row(code="PREVIOUS23")
    repo = FakeCodeRepo(unrevoked=previous)
    service = _code_service(monkeypatch, repo=repo, authz=FakeAuthz(allowed_estate_ids={4}))
    actor = SimpleNamespace(user_id=3, role=UserRole.hoa_admin.value)

    result = asyncio.run(_rotate(service, actor))
    assert repo.revoked and repo.revoked[0][0] is previous
    assert previous.revoked_at is not None
    assert repo.added is not None
    assert repo.added["estate_id"] == 4
    assert repo.added["created_by"] == 3
    assert len(repo.added["code"]) == CODE_LENGTH
    assert result.expires_at is not None
    assert service._db.commits == 1


async def _rotate(service, actor):
    return await service.rotate(actor, estate_id=4, expires_in_days=30)


def test_rotate_without_expiry_creates_a_code_that_never_expires(monkeypatch) -> None:
    import asyncio

    repo = FakeCodeRepo()
    service = _code_service(monkeypatch, repo=repo, authz=FakeAuthz(allowed_estate_ids={4}))
    actor = SimpleNamespace(user_id=3, role=UserRole.hoa_admin.value)

    result = asyncio.run(service.rotate(actor, estate_id=4, expires_in_days=None))

    assert repo.added["expires_at"] is None
    assert result.expires_at is None


def test_rotate_is_denied_for_an_estate_the_admin_does_not_administer(monkeypatch) -> None:
    import asyncio

    repo = FakeCodeRepo()
    service = _code_service(monkeypatch, repo=repo, authz=FakeAuthz(allowed_estate_ids={1}))
    actor = SimpleNamespace(user_id=3, role=UserRole.hoa_admin.value)

    with pytest.raises(ForbiddenException):
        asyncio.run(service.rotate(actor, estate_id=4, expires_in_days=None))
    assert repo.added is None
    assert service._db.commits == 0


def test_current_code_is_404_when_none_is_active(monkeypatch) -> None:
    import asyncio

    repo = FakeCodeRepo(active=None)
    service = _code_service(monkeypatch, repo=repo, authz=FakeAuthz(allowed_estate_ids={4}))
    actor = SimpleNamespace(user_id=3, role=UserRole.hoa_admin.value)

    with pytest.raises(NotFoundException):
        asyncio.run(service.get_current(actor, estate_id=4))


def test_current_code_returns_the_active_code(monkeypatch) -> None:
    import asyncio

    row = _code_row(code="CURRENT234")
    repo = FakeCodeRepo(active=row)
    service = _code_service(monkeypatch, repo=repo, authz=FakeAuthz(allowed_estate_ids={4}))
    actor = SimpleNamespace(user_id=3, role=UserRole.hoa_admin.value)

    result = asyncio.run(service.get_current(actor, estate_id=4))

    assert result == JoinCodeResponse(
        code="CURRENT234",
        estate_id=4,
        created_at=row.created_at,
        expires_at=None,
    )


# --------------------------------------------------------------------------- #
# 6. Membership service: join, list and remove
# --------------------------------------------------------------------------- #
def _unit(**overrides):
    row = {"unit_id": 21, "estate_id": 4, "unit_no": "A-1"}
    row.update(overrides)
    return SimpleNamespace(**row)


def _membership(**overrides):
    row = {
        "membership_id": 31,
        "user_id": 8,
        "estate_id": 4,
        "property_id": 21,
        "membership_role": UserRole.resident.value,
        "created_at": datetime.now(timezone.utc),
    }
    row.update(overrides)
    return SimpleNamespace(**row)


class FakePropertyRepo2:
    def __init__(self, unit):
        self._unit = unit
        self.lookups: list[tuple[int, str]] = []

    async def get_by_unit_no_in_estate_ci(self, *, estate_id, unit_no):
        self.lookups.append((estate_id, unit_no))
        return self._unit


class FakeEstateRepo2:
    def __init__(self, estate):
        self._estate = estate

    async def get_by_id(self, estate_id):
        return self._estate


class FakeMembershipRepo2:
    def __init__(self, *, existing=None, rows=None, total=None, by_id=None, explode=False):
        self._existing = existing
        self._rows = rows or []
        self._total = total if total is not None else len(self._rows)
        self._by_id = by_id
        self.added: dict | None = None
        self.deleted: list = []
        self._explode = explode

    async def get_for_user_and_estate(self, *, user_id, estate_id):
        return self._existing

    async def add(self, **fields):
        if self._explode:
            raise AssertionError("no membership may be created")
        self.added = fields
        return _membership(**fields)

    async def get_by_id_in_estate(self, *, membership_id, estate_id):
        if self._by_id is not None and self._by_id.estate_id == estate_id:
            return self._by_id
        return None

    async def list_members_for_estate(self, *, estate_id, role=None, offset=0, limit=100):
        return list(self._rows)

    async def count_members_for_estate(self, *, estate_id, role=None):
        return self._total

    async def delete(self, membership):
        self.deleted.append(membership)


class FakeEventRepo2:
    def __init__(self):
        self.records: list[dict] = []

    async def record(self, **fields):
        self.records.append(fields)
        return SimpleNamespace(event_id=len(self.records), **fields)


class FakeCodeRepo2:
    def __init__(self, row):
        self._row = row

    async def get_by_code(self, code):
        return self._row


def _membership_service(
    monkeypatch,
    *,
    codes,
    memberships,
    events,
    property_repo,
    estate_repo,
    authz=None,
    session=None,
    limiter=None,
):
    import app.identity.services.membership_service as module

    monkeypatch.setattr(module, "EstateJoinCodeRepository", lambda _db: codes)
    monkeypatch.setattr(module, "EstateMembershipRepository", lambda _db: memberships)
    monkeypatch.setattr(module, "EstateMembershipEventRepository", lambda _db: events)
    monkeypatch.setattr(module, "PropertyRepository", lambda _db: property_repo)
    monkeypatch.setattr(module, "EstateRepository", lambda _db: estate_repo)
    if authz is not None:
        monkeypatch.setattr(module, "EstateAuthorizationService", lambda _db: authz)
    return module.MembershipService(session or FakeSession(), limiter=limiter)


def _resident(user_id: int = 8):
    return SimpleNamespace(user_id=user_id, role=UserRole.resident.value)


def test_join_creates_the_membership_and_one_joined_event_in_one_transaction(monkeypatch) -> None:
    import asyncio

    session = FakeSession()
    memberships = FakeMembershipRepo2()
    events = FakeEventRepo2()
    code_row = _code_row(code="ABCDEFGHJK", estate_id=4)
    service = _membership_service(
        monkeypatch,
        codes=FakeCodeRepo2(code_row),
        memberships=memberships,
        events=events,
        property_repo=FakePropertyRepo2(_unit()),
        estate_repo=FakeEstateRepo2(SimpleNamespace(estate_id=4, name="Zambezi")),
        session=session,
    )

    result = asyncio.run(
        service.join_with_code(_resident(), MembershipJoinRequest(code="abcd-efghjk", unit_no=" a-1 "))
    )

    assert session.commits == 1
    assert memberships.added == {
        "user_id": 8,
        "estate_id": 4,
        "property_id": 21,
        "membership_role": UserRole.resident.value,
        "join_code_id": 1,
    }
    assert events.records == [
        {
            "estate_id": 4,
            "user_id": 8,
            "membership_role": UserRole.resident.value,
            "property_id": 21,
            "event_type": "joined",
            "actor_user_id": 8,
        }
    ]
    assert result == MembershipJoinResponse(
        estate_id=4,
        estate_name="Zambezi",
        unit_id=21,
        unit_no="A-1",
        role=UserRole.resident.value,
    )


def test_join_returns_a_uniform_404_for_an_unknown_code(monkeypatch) -> None:
    import asyncio

    session = FakeSession()
    limiter = JoinAttemptLimiter(clock=FakeClock())
    service = _membership_service(
        monkeypatch,
        codes=FakeCodeRepo2(None),
        memberships=FakeMembershipRepo2(),
        events=FakeEventRepo2(),
        property_repo=FakePropertyRepo2(_unit()),
        estate_repo=FakeEstateRepo2(SimpleNamespace(estate_id=4, name="Zambezi")),
        session=session,
        limiter=limiter,
    )

    with pytest.raises(NotFoundException) as excinfo:
        asyncio.run(
            service.join_with_code(_resident(), MembershipJoinRequest(code="ZZZZZZZZZZ", unit_no="A-1"))
        )

    assert excinfo.value.detail == "That code is not valid."
    assert "ZZZZZZZZZZ" not in str(excinfo.value.detail)
    assert session.commits == 0
    assert limiter.failures_in_window(8) == 1


@pytest.mark.parametrize("kind", ["revoked", "expired"])
def test_join_rejects_a_revoked_or_expired_code_the_same_way(monkeypatch, kind) -> None:
    import asyncio

    overrides = {"revoked_at": datetime.now(timezone.utc)} if kind == "revoked" else {
        "expires_at": datetime.now(timezone.utc) - timedelta(minutes=1)
    }
    limiter = JoinAttemptLimiter(clock=FakeClock())
    service = _membership_service(
        monkeypatch,
        codes=FakeCodeRepo2(_code_row(**overrides)),
        memberships=FakeMembershipRepo2(),
        events=FakeEventRepo2(),
        property_repo=FakePropertyRepo2(_unit()),
        estate_repo=FakeEstateRepo2(SimpleNamespace(estate_id=4, name="Zambezi")),
        limiter=limiter,
    )

    with pytest.raises(NotFoundException) as excinfo:
        asyncio.run(
            service.join_with_code(_resident(), MembershipJoinRequest(code="ABCDEFGHJK", unit_no="A-1"))
        )

    assert excinfo.value.detail == "That code is not valid."
    assert limiter.failures_in_window(8) == 1


def test_join_returns_a_uniform_404_when_the_code_is_blank(monkeypatch) -> None:
    import asyncio

    limiter = JoinAttemptLimiter(clock=FakeClock())
    service = _membership_service(
        monkeypatch,
        codes=FakeCodeRepo2(_code_row()),
        memberships=FakeMembershipRepo2(),
        events=FakeEventRepo2(),
        property_repo=FakePropertyRepo2(_unit()),
        estate_repo=FakeEstateRepo2(SimpleNamespace(estate_id=4, name="Zambezi")),
        limiter=limiter,
    )

    with pytest.raises(NotFoundException):
        asyncio.run(
            service.join_with_code(_resident(), MembershipJoinRequest(code="- -", unit_no="A-1"))
        )
    assert limiter.failures_in_window(8) == 1


def test_join_is_rate_limited_after_five_failed_code_attempts(monkeypatch) -> None:
    import asyncio

    clock = FakeClock()
    limiter = JoinAttemptLimiter(clock=clock)
    session = FakeSession()
    service = _membership_service(
        monkeypatch,
        codes=FakeCodeRepo2(None),
        memberships=FakeMembershipRepo2(),
        events=FakeEventRepo2(),
        property_repo=FakePropertyRepo2(_unit()),
        estate_repo=FakeEstateRepo2(SimpleNamespace(estate_id=4, name="Zambezi")),
        session=session,
        limiter=limiter,
    )

    for _ in range(5):
        with pytest.raises(NotFoundException):
            asyncio.run(
                service.join_with_code(
                    _resident(), MembershipJoinRequest(code="BADCODE234", unit_no="A-1")
                )
            )

    with pytest.raises(RateLimitException):
        asyncio.run(
            service.join_with_code(_resident(), MembershipJoinRequest(code="BADCODE234", unit_no="A-1"))
        )

    clock.advance(901)
    with pytest.raises(NotFoundException):  # allowed again, then fails on the code
        asyncio.run(
            service.join_with_code(_resident(), MembershipJoinRequest(code="BADCODE234", unit_no="A-1"))
        )


def test_join_404s_on_a_unit_that_is_not_in_the_code_s_estate(monkeypatch) -> None:
    import asyncio

    limiter = JoinAttemptLimiter(clock=FakeClock())
    property_repo = FakePropertyRepo2(None)
    service = _membership_service(
        monkeypatch,
        codes=FakeCodeRepo2(_code_row(estate_id=4)),
        memberships=FakeMembershipRepo2(),
        events=FakeEventRepo2(),
        property_repo=property_repo,
        estate_repo=FakeEstateRepo2(SimpleNamespace(estate_id=4, name="Zambezi")),
        limiter=limiter,
    )

    with pytest.raises(NotFoundException):
        asyncio.run(
            service.join_with_code(_resident(), MembershipJoinRequest(code="ABCDEFGHJK", unit_no="A-1"))
        )
    assert property_repo.lookups == [(4, "A-1")]
    # A valid code with an unknown unit is not a failed code attempt.
    assert limiter.failures_in_window(8) == 0


def test_join_409s_when_the_user_is_already_a_member(monkeypatch) -> None:
    import asyncio

    session = FakeSession()
    memberships = FakeMembershipRepo2(existing=_membership())
    events = FakeEventRepo2()
    service = _membership_service(
        monkeypatch,
        codes=FakeCodeRepo2(_code_row(estate_id=4)),
        memberships=memberships,
        events=events,
        property_repo=FakePropertyRepo2(_unit()),
        estate_repo=FakeEstateRepo2(SimpleNamespace(estate_id=4, name="Zambezi")),
        session=session,
    )

    with pytest.raises(ConflictException):
        asyncio.run(
            service.join_with_code(_resident(), MembershipJoinRequest(code="ABCDEFGHJK", unit_no="A-1"))
        )
    assert memberships.added is None
    assert events.records == []
    assert session.commits == 0


def test_join_survives_a_concurrent_duplicate_as_a_409(monkeypatch) -> None:
    import asyncio

    from sqlalchemy.exc import IntegrityError

    class ExplodingSession(FakeSession):
        async def commit(self) -> None:
            raise IntegrityError("stmt", {}, Exception("duplicate key value"))

    session = ExplodingSession()
    service = _membership_service(
        monkeypatch,
        codes=FakeCodeRepo2(_code_row(estate_id=4)),
        memberships=FakeMembershipRepo2(),
        events=FakeEventRepo2(),
        property_repo=FakePropertyRepo2(_unit()),
        estate_repo=FakeEstateRepo2(SimpleNamespace(estate_id=4, name="Zambezi")),
        session=session,
    )

    with pytest.raises(ConflictException):
        asyncio.run(
            service.join_with_code(_resident(), MembershipJoinRequest(code="ABCDEFGHJK", unit_no="A-1"))
        )
    assert session.rollbacks == 1


def test_list_members_requires_estate_admin_and_paginates_newest_first(monkeypatch) -> None:
    import asyncio

    rows = [
        SimpleNamespace(
            membership_id=31,
            membership_role="resident",
            user_id=8,
            full_name="Nandi Dlamini",
            email="nandi@example.com",
            unit_no="A-1",
            created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        ),
        SimpleNamespace(
            membership_id=30,
            membership_role="service_provider",
            user_id=9,
            full_name="Pete",
            email="pete@example.com",
            unit_no=None,
            created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        ),
    ]
    memberships = FakeMembershipRepo2(rows=rows, total=2)
    authz = FakeAuthz(allowed_estate_ids={4})
    service = _membership_service(
        monkeypatch,
        codes=FakeCodeRepo2(None),
        memberships=memberships,
        events=FakeEventRepo2(),
        property_repo=FakePropertyRepo2(None),
        estate_repo=FakeEstateRepo2(None),
        authz=authz,
    )

    page = asyncio.run(
        service.list_members(
            SimpleNamespace(user_id=3, role=UserRole.hoa_admin.value),
            estate_id=4,
            role=None,
            page=1,
            page_size=20,
        )
    )

    assert authz.calls == [4]
    assert page.total == 2
    assert page.size == 20
    assert page.pages == 1
    assert [item.membership_id for item in page.items] == [31, 30]
    assert page.items[0].unit_no == "A-1"
    assert page.items[1].unit_no is None


def test_list_members_is_denied_for_an_estate_you_do_not_administer(monkeypatch) -> None:
    import asyncio

    service = _membership_service(
        monkeypatch,
        codes=FakeCodeRepo2(None),
        memberships=FakeMembershipRepo2(),
        events=FakeEventRepo2(),
        property_repo=FakePropertyRepo2(None),
        estate_repo=FakeEstateRepo2(None),
        authz=FakeAuthz(allowed_estate_ids={1}),
    )

    with pytest.raises(ForbiddenException):
        asyncio.run(
            service.list_members(
                SimpleNamespace(user_id=3, role=UserRole.hoa_admin.value),
                estate_id=4,
                role=None,
                page=1,
                page_size=20,
            )
        )


def test_remove_member_deletes_only_in_estate_rows_and_writes_a_removed_event(monkeypatch) -> None:
    import asyncio

    session = FakeSession()
    membership = _membership()
    memberships = FakeMembershipRepo2(by_id=membership)
    events = FakeEventRepo2()
    service = _membership_service(
        monkeypatch,
        codes=FakeCodeRepo2(None),
        memberships=memberships,
        events=events,
        property_repo=FakePropertyRepo2(None),
        estate_repo=FakeEstateRepo2(None),
        authz=FakeAuthz(allowed_estate_ids={4}),
        session=session,
    )

    asyncio.run(
        service.remove_member(
            SimpleNamespace(user_id=3, role=UserRole.hoa_admin.value),
            membership_id=31,
            estate_id=4,
        )
    )

    assert memberships.deleted == [membership]
    assert events.records == [
        {
            "estate_id": 4,
            "user_id": 8,
            "membership_role": UserRole.resident.value,
            "property_id": 21,
            "event_type": "removed",
            "actor_user_id": 3,
        }
    ]
    assert session.commits == 1


def test_remove_member_refuses_an_admin_membership(monkeypatch) -> None:
    import asyncio

    session = FakeSession()
    memberships = FakeMembershipRepo2(
        by_id=_membership(membership_id=31, membership_role=UserRole.hoa_admin.value, property_id=None)
    )
    events = FakeEventRepo2()
    service = _membership_service(
        monkeypatch,
        codes=FakeCodeRepo2(None),
        memberships=memberships,
        events=events,
        property_repo=FakePropertyRepo2(None),
        estate_repo=FakeEstateRepo2(None),
        authz=FakeAuthz(allowed_estate_ids={4}),
        session=session,
    )

    with pytest.raises(ConflictException):
        asyncio.run(
            service.remove_member(
                SimpleNamespace(user_id=3, role=UserRole.hoa_admin.value),
                membership_id=31,
                estate_id=4,
            )
        )
    assert memberships.deleted == []
    assert events.records == []
    assert session.commits == 0


def test_remove_member_of_another_estate_is_a_404(monkeypatch) -> None:
    import asyncio

    session = FakeSession()
    memberships = FakeMembershipRepo2(by_id=_membership(estate_id=99))
    service = _membership_service(
        monkeypatch,
        codes=FakeCodeRepo2(None),
        memberships=memberships,
        events=FakeEventRepo2(),
        property_repo=FakePropertyRepo2(None),
        estate_repo=FakeEstateRepo2(None),
        authz=FakeAuthz(allowed_estate_ids={4}),
        session=session,
    )

    with pytest.raises(NotFoundException):
        asyncio.run(
            service.remove_member(
                SimpleNamespace(user_id=3, role=UserRole.hoa_admin.value),
                membership_id=31,
                estate_id=4,
            )
        )
    assert memberships.deleted == []
    assert session.commits == 0


# --------------------------------------------------------------------------- #
# 7. Bulk units: all-or-nothing, estate-derived fields
# --------------------------------------------------------------------------- #
class FakeEstateRepo3:
    def __init__(self, estate):
        self._estate = estate

    async def get_by_id(self, estate_id):
        return self._estate


class FakePropertyRepo3:
    def __init__(self, *, existing_unit_nos=(), explode_at=None):
        self._existing = set(existing_unit_nos)
        self.added: list[dict] = []
        self._explode_at = explode_at

    async def list_unit_nos_in_estate(self, *, estate_id):
        return set(self._existing)

    async def add(self, **fields):
        if self._explode_at is not None and len(self.added) == self._explode_at:
            from sqlalchemy.exc import IntegrityError

            raise IntegrityError("stmt", {}, Exception("duplicate key value"))
        self.added.append(fields)
        return SimpleNamespace(
            unit_id=100 + len(self.added),
            estate_id=fields["estate_id"],
            unit_no=fields["unit_no"],
            complex_name=fields["complex_name"],
            street_address=fields["street_address"],
            suburb=fields["suburb"],
            size_m2=fields["size_m2"],
            bedrooms=fields["bedrooms"],
            bathrooms=fields["bathrooms"],
        )


def _bulk_service(monkeypatch, *, properties, estates, authz, session=None):
    import app.property.services.property_service as module

    monkeypatch.setattr(module, "PropertyRepository", lambda _db: properties)
    monkeypatch.setattr(module, "EstateRepository", lambda _db: estates)
    monkeypatch.setattr(module, "EstateAuthorizationService", lambda _db: authz)
    return PropertyService(session or FakeSession())


def _bulk_items(*unit_nos):
    return BulkUnitsRequest.model_validate(
        {
            "units": [
                {"unit_no": unit_no, "street_address": f"{unit_no} Road", "bedrooms": 2}
                for unit_no in unit_nos
            ]
        }
    )


def test_bulk_units_takes_complex_name_and_suburb_from_the_estate(monkeypatch) -> None:
    import asyncio

    session = FakeSession()
    properties = FakePropertyRepo3()
    estate = SimpleNamespace(estate_id=4, name="Zambezi Country Estate", suburb="Montana")
    service = _bulk_service(
        monkeypatch,
        properties=properties,
        estates=FakeEstateRepo3(estate),
        authz=FakeAuthz(allowed_estate_ids={4}),
        session=session,
    )

    result = asyncio.run(
        service.create_units_bulk(
            _bulk_items("A-1", "A-2"),
            estate_id=4,
            actor=SimpleNamespace(user_id=3, role=UserRole.hoa_admin.value),
        )
    )

    assert session.commits == 1
    assert [row["unit_no"] for row in properties.added] == ["A-1", "A-2"]
    assert {row["complex_name"] for row in properties.added} == {"Zambezi Country Estate"}
    assert {row["suburb"] for row in properties.added} == {"Montana"}
    assert {row["estate_id"] for row in properties.added} == {4}
    assert [item.unit_no for item in result] == ["A-1", "A-2"]


def test_bulk_units_is_denied_for_an_estate_the_admin_does_not_administer(monkeypatch) -> None:
    import asyncio

    properties = FakePropertyRepo3()
    service = _bulk_service(
        monkeypatch,
        properties=properties,
        estates=FakeEstateRepo3(SimpleNamespace(estate_id=4, name="X", suburb="Y")),
        authz=FakeAuthz(allowed_estate_ids={1}),
    )

    with pytest.raises(ForbiddenException):
        asyncio.run(
            service.create_units_bulk(
                _bulk_items("A-1"),
                estate_id=4,
                actor=SimpleNamespace(user_id=3, role=UserRole.hoa_admin.value),
            )
        )
    assert properties.added == []


def test_bulk_units_rejects_duplicates_inside_the_request_and_inserts_nothing(monkeypatch) -> None:
    import asyncio

    session = FakeSession()
    properties = FakePropertyRepo3()
    service = _bulk_service(
        monkeypatch,
        properties=properties,
        estates=FakeEstateRepo3(SimpleNamespace(estate_id=4, name="X", suburb="Y")),
        authz=FakeAuthz(allowed_estate_ids={4}),
        session=session,
    )

    with pytest.raises(ConflictException) as excinfo:
        asyncio.run(
            service.create_units_bulk(
                _bulk_items("A-1", "A-2", "A-1"),
                estate_id=4,
                actor=SimpleNamespace(user_id=3, role=UserRole.hoa_admin.value),
            )
        )

    assert "A-1" in str(excinfo.value.detail)
    assert properties.added == []
    assert session.commits == 0


def test_bulk_units_rejects_units_that_already_exist_in_the_estate(monkeypatch) -> None:
    import asyncio

    session = FakeSession()
    properties = FakePropertyRepo3(existing_unit_nos={"A-1", "A-9"})
    service = _bulk_service(
        monkeypatch,
        properties=properties,
        estates=FakeEstateRepo3(SimpleNamespace(estate_id=4, name="X", suburb="Y")),
        authz=FakeAuthz(allowed_estate_ids={4}),
        session=session,
    )

    with pytest.raises(ConflictException) as excinfo:
        asyncio.run(
            service.create_units_bulk(
                _bulk_items("A-1", "A-2"),
                estate_id=4,
                actor=SimpleNamespace(user_id=3, role=UserRole.hoa_admin.value),
            )
        )

    assert "A-1" in str(excinfo.value.detail)
    assert "A-2" not in str(excinfo.value.detail)
    assert properties.added == []


def test_bulk_units_rolls_back_when_the_database_rejects_a_race(monkeypatch) -> None:
    import asyncio

    session = FakeSession()
    properties = FakePropertyRepo3(explode_at=1)
    service = _bulk_service(
        monkeypatch,
        properties=properties,
        estates=FakeEstateRepo3(SimpleNamespace(estate_id=4, name="X", suburb="Y")),
        authz=FakeAuthz(allowed_estate_ids={4}),
        session=session,
    )

    with pytest.raises(ConflictException):
        asyncio.run(
            service.create_units_bulk(
                _bulk_items("A-1", "A-2"),
                estate_id=4,
                actor=SimpleNamespace(user_id=3, role=UserRole.hoa_admin.value),
            )
        )
    assert session.rollbacks == 1
    assert session.commits == 0


# --------------------------------------------------------------------------- #
# 8. Route guards: the code never appears in a URL, and who may call what
# --------------------------------------------------------------------------- #
def _route_client(*, role: str) -> TestClient:
    test_app = FastAPI()
    test_app.include_router(create_api_router(True))
    test_app.dependency_overrides[get_db] = lambda: object()
    test_app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        user_id=7, role=role
    )
    return TestClient(test_app)


def _all_paths() -> set[str]:
    app = FastAPI()
    app.include_router(create_api_router(True))
    # The OpenAPI schema is the flat list of paths, whatever the router internals do.
    return set(app.openapi()["paths"])


def test_join_uses_a_body_not_a_url_for_the_code() -> None:
    paths = _all_paths()
    assert "/api/v1/memberships/join" in paths
    assert "/api/v1/join-codes" in paths
    # No route may take a code as a path parameter, in any spelling.
    assert not any("{" in path and "code" in path for path in paths)


def test_join_is_rejected_for_hoa_admin_and_service_provider_at_the_route() -> None:
    body = {"code": "ABCDEFGHJK", "unit_no": "A-1"}
    for role in ("hoa_admin", "service_provider", "estate_agent", "platform_admin"):
        response = _route_client(role=role).post("/api/v1/memberships/join", json=body)
        assert response.status_code == 403, (role, response.text)


def test_membership_and_code_endpoints_require_authentication() -> None:
    test_app = FastAPI()
    test_app.include_router(create_api_router(True))
    test_app.dependency_overrides[get_db] = lambda: object()
    anonymous = TestClient(test_app)

    assert anonymous.get("/api/v1/join-codes/current?estate_id=1").status_code == 401
    assert anonymous.post("/api/v1/join-codes?estate_id=1", json={}).status_code == 401
    assert anonymous.get("/api/v1/memberships?estate_id=1").status_code == 401
    assert anonymous.delete("/api/v1/memberships/1?estate_id=1").status_code == 401
    assert anonymous.post(
        "/api/v1/properties/bulk?estate_id=1",
        json={"units": [{"unit_no": "A-1", "street_address": "1 Road"}]},
    ).status_code == 401


def test_join_code_endpoints_reject_a_payload_that_carries_the_estate_in_the_body() -> None:
    response = _route_client(role="hoa_admin").post(
        "/api/v1/join-codes?estate_id=1", json={"estate_id": 1}
    )
    assert response.status_code == 422


def test_join_body_must_not_be_usable_as_a_query_string() -> None:
    # The code travels in the body only: a GET with the code in the query string
    # must never reach a handler.
    response = _route_client(role="resident").get(
        "/api/v1/memberships/join?code=ABCDEFGHJK&unit_no=A-1"
    )
    assert response.status_code == 405


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
        command.upgrade(cfg, "head", sql=True)
    else:
        command.downgrade(cfg, "b1e4f7a9c2d5:d9f2a4c7e1b3", sql=True)
    return buffer.getvalue()


def test_migration_upgrade_sql_creates_the_new_tables_and_indexes() -> None:
    sql = _offline_sql("up")
    assert "CREATE TABLE estate_join_codes" in sql
    assert "CREATE TABLE estate_membership_events" in sql
    assert "uq_estate_join_codes_code" in sql
    assert "uq_estate_join_codes_one_active_per_estate" in sql
    assert "ck_estate_membership_events_type_allowed" in sql
    assert "uq_membership_user_estate_join" in sql
    assert "join_code_id" in sql


def test_migration_downgrade_sql_drops_what_the_upgrade_added() -> None:
    sql = _offline_sql("down")
    assert "DROP INDEX uq_membership_user_estate_join" in sql
    assert "DROP TABLE estate_membership_events" in sql
    assert "DROP TABLE estate_join_codes" in sql
    assert "join_code_id" in sql


def test_migration_declares_a_single_new_head_on_the_previous_head() -> None:
    import importlib.util
    import pathlib

    path = (
        pathlib.Path(__file__).resolve().parent.parent
        / "alembic"
        / "versions"
        / "b1e4f7a9c2d5_add_estate_join_codes_and_membership_events.py"
    )
    spec = importlib.util.spec_from_file_location("onb2_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "b1e4f7a9c2d5"
    assert module.down_revision == "d9f2a4c7e1b3"
    assert callable(module.downgrade)
    assert callable(module.upgrade)


# --------------------------------------------------------------------------- #
# 10. Integration: real database only. Auto-skip without TEST_DATABASE_URL.
# --------------------------------------------------------------------------- #
PASSWORD = "correct-horse-battery-staple"
BASE = "/api/v1"


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _new_estate_world(client, *, name: str, email: str, unit_nos=("A-1",)):
    """Sign up an estate admin, add units, share a code. Returns (headers, code, estate_id, unit_ids)."""
    registration = await client.post(
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
    headers = _bearer(registration.json()["access_token"])

    estates = await client.get(f"{BASE}/auth/estates", headers=headers)
    estate_id = estates.json()["estates"][0]["estate_id"]

    units = await client.post(
        f"{BASE}/properties/bulk?estate_id={estate_id}",
        json={
            "units": [
                {"unit_no": unit_no, "street_address": f"{unit_no} Ridge Close", "bedrooms": 3}
                for unit_no in unit_nos
            ]
        },
        headers=headers,
    )
    assert units.status_code == 201, units.text
    unit_ids = [item["id"] for item in units.json()]

    created = await client.post(f"{BASE}/join-codes?estate_id={estate_id}", json={}, headers=headers)
    assert created.status_code == 201, created.text
    return headers, created.json()["code"], estate_id, unit_ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_resident_journey_bulk_units_code_join_and_removal(db_session, async_client) -> None:
    from app.identity.repositories.estate_membership_event_repository import (
        EstateMembershipEventRepository,
    )

    admin_headers, code, estate_id, unit_ids = await _new_estate_world(
        async_client, name="Onb2 Journey Estate", email="onb2_admin@example.com", unit_nos=("A-1", "A-2")
    )

    # 1. The list of members is empty until someone joins.
    listed = await async_client.get(f"{BASE}/memberships?estate_id={estate_id}", headers=admin_headers)
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 1  # the estate admin's own membership
    assert {item["role"] for item in listed.json()["items"]} == {"hoa_admin"}

    # 2. A resident registers and joins with the code and their unit number.
    registered = await async_client.post(
        f"{BASE}/auth/register",
        json={
            "full_name": "Nandi Dlamini",
            "email": "onb2_resident@example.com",
            "password": PASSWORD,
        },
    )
    assert registered.status_code == 201, registered.text
    resident_headers = _bearer(registered.json()["access_token"])

    joined = await async_client.post(
        f"{BASE}/memberships/join",
        json={"code": f" {code.lower()} ", "unit_no": " a-1 "},
        headers=resident_headers,
    )
    assert joined.status_code == 201, joined.text
    body = joined.json()
    assert body == {
        "estate_id": estate_id,
        "estate_name": "Onb2 Journey Estate",
        "unit_id": unit_ids[0],
        "unit_no": "A-1",
        "role": "resident",
    }
    assert code not in joined.text

    # 3. /auth/estates reflects the join immediately.
    estates = await async_client.get(f"{BASE}/auth/estates", headers=resident_headers)
    assert [e["estate_name"] for e in estates.json()["estates"]] == ["Onb2 Journey Estate"]
    assert estates.json()["estates"][0]["property_ids"] == [unit_ids[0]]

    # 4. Joining a second time is a 409.
    again = await async_client.post(
        f"{BASE}/memberships/join",
        json={"code": code, "unit_no": "A-1"},
        headers=resident_headers,
    )
    assert again.status_code == 409, again.text

    # 5. The admin sees the resident, newest first, with the unit number.
    listed = await async_client.get(f"{BASE}/memberships?estate_id={estate_id}", headers=admin_headers)
    items = listed.json()["items"]
    assert listed.json()["total"] == 2
    assert items[0]["role"] == "resident"
    assert items[0]["unit_no"] == "A-1"
    assert items[0]["email"] == "onb2_resident@example.com"
    assert items[0]["full_name"] == "Nandi Dlamini"
    assert items[0]["joined_at"]
    assert items[1]["role"] == "hoa_admin"

    # 6. A 'joined' event was written in the same transaction.
    events = await EstateMembershipEventRepository(db_session).list_for_estate(estate_id=estate_id)
    assert len(events) == 1
    assert events[0].event_type == "joined"
    assert events[0].property_id == unit_ids[0]
    assert events[0].membership_role == "resident"
    assert events[0].occurred_at is not None

    # 7. The admin removes the resident; the row and an event both go.
    removed = await async_client.delete(
        f"{BASE}/memberships/{items[0]['membership_id']}?estate_id={estate_id}",
        headers=admin_headers,
    )
    assert removed.status_code == 204, removed.text

    events = await EstateMembershipEventRepository(db_session).list_for_estate(estate_id=estate_id)
    assert [e.event_type for e in events] == ["joined", "removed"]
    assert events[-1].actor_user_id is not None

    # 8. Access is gone immediately, with the old token still in hand.
    estates = await async_client.get(f"{BASE}/auth/estates", headers=resident_headers)
    assert estates.json()["estates"] == []
    denied = await async_client.get(f"{BASE}/complaints?estate_id={estate_id}", headers=resident_headers)
    assert denied.status_code == 403, denied.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_resident_can_report_only_for_their_own_unit_and_sees_no_one_else(db_session, async_client) -> None:
    admin_headers, code, estate_id, unit_ids = await _new_estate_world(
        async_client, name="Onb2 Complaint Estate", email="onb2_c_admin@example.com", unit_nos=("B-1", "B-2")
    )

    async def _join(email: str, unit_no: str) -> dict:
        registered = await async_client.post(
            f"{BASE}/auth/register",
            json={"full_name": "Resident", "email": email, "password": PASSWORD},
        )
        assert registered.status_code == 201, registered.text
        headers = _bearer(registered.json()["access_token"])
        joined = await async_client.post(
            f"{BASE}/memberships/join",
            json={"code": code, "unit_no": unit_no},
            headers=headers,
        )
        assert joined.status_code == 201, joined.text
        return headers

    alice = await _join("onb2_alice@example.com", "B-1")
    bob = await _join("onb2_bob@example.com", "B-2")

    mine = await async_client.post(
        f"{BASE}/complaints?estate_id={estate_id}",
        json={"unit_id": unit_ids[0], "category": "other", "description": "My own unit"},
        headers=alice,
    )
    assert mine.status_code == 201, mine.text

    not_mine = await async_client.post(
        f"{BASE}/complaints?estate_id={estate_id}",
        json={"unit_id": unit_ids[1], "category": "other", "description": "Bob's unit"},
        headers=alice,
    )
    assert not_mine.status_code == 403, not_mine.text

    bob_complaint = await async_client.post(
        f"{BASE}/complaints?estate_id={estate_id}",
        json={"unit_id": unit_ids[1], "category": "other", "description": "Bob only"},
        headers=bob,
    )
    assert bob_complaint.status_code == 201, bob_complaint.text

    alice_list = await async_client.get(f"{BASE}/complaints?estate_id={estate_id}", headers=alice)
    assert alice_list.status_code == 200, alice_list.text
    assert [c["description"] for c in alice_list.json()["items"]] == ["My own unit"]

    admin_list = await async_client.get(f"{BASE}/complaints?estate_id={estate_id}", headers=admin_headers)
    assert admin_list.status_code == 200, admin_list.text
    assert admin_list.json()["total"] == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_code_rotation_leaves_exactly_one_active_code(db_session, async_client) -> None:
    from sqlalchemy import text

    admin_headers, first_code, estate_id, _ = await _new_estate_world(
        async_client, name="Onb2 Rotation Estate", email="onb2_rot@example.com"
    )

    current = await async_client.get(f"{BASE}/join-codes/current?estate_id={estate_id}", headers=admin_headers)
    assert current.status_code == 200, current.text
    assert current.json()["code"] == first_code

    rotated = await async_client.post(
        f"{BASE}/join-codes?estate_id={estate_id}", json={"expires_in_days": 7}, headers=admin_headers
    )
    assert rotated.status_code == 201, rotated.text
    second_code = rotated.json()["code"]
    assert second_code != first_code

    rows = (
        await db_session.execute(
            text(
                "SELECT count(*) FROM estate_join_codes "
                "WHERE estate_id = :eid AND revoked_at IS NULL"
            ),
            {"eid": estate_id},
        )
    ).scalar_one()
    assert rows == 1

    current = await async_client.get(f"{BASE}/join-codes/current?estate_id={estate_id}", headers=admin_headers)
    assert current.json()["code"] == second_code

    # The revoked code no longer joins anyone.
    registered = await async_client.post(
        f"{BASE}/auth/register",
        json={"full_name": "Late", "email": "onb2_late@example.com", "password": PASSWORD},
    )
    late_headers = _bearer(registered.json()["access_token"])
    stale = await async_client.post(
        f"{BASE}/memberships/join",
        json={"code": first_code, "unit_no": "A-1"},
        headers=late_headers,
    )
    assert stale.status_code == 404, stale.text
    assert stale.json()["detail"]["message"] == "That code is not valid."


@pytest.mark.integration
@pytest.mark.asyncio
async def test_join_after_five_bad_codes_is_rate_limited(db_session, async_client) -> None:
    from app.identity.services.join_attempt_limiter import join_attempt_limiter

    _, code, estate_id, _ = await _new_estate_world(
        async_client, name="Onb2 Limit Estate", email="onb2_limit_admin@example.com"
    )
    registered = await async_client.post(
        f"{BASE}/auth/register",
        json={"full_name": "Limiter", "email": "onb2_limit@example.com", "password": PASSWORD},
    )
    headers = _bearer(registered.json()["access_token"])
    join_attempt_limiter.reset_all()

    for _ in range(5):
        bad = await async_client.post(
            f"{BASE}/memberships/join",
            json={"code": "ZZZZZZZZZZ", "unit_no": "A-1"},
            headers=headers,
        )
        assert bad.status_code == 404, bad.text

    limited = await async_client.post(
        f"{BASE}/memberships/join",
        json={"code": code, "unit_no": "A-1"},
        headers=headers,
    )
    assert limited.status_code == 429, limited.text
    assert limited.json()["detail"]["code"] == "RATE_LIMITED"

    join_attempt_limiter.reset_all()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_code_never_appears_in_logs_or_in_an_error_body(db_session, async_client, caplog) -> None:
    import logging

    _, code, estate_id, _ = await _new_estate_world(
        async_client, name="Onb2 Secrets Estate", email="onb2_secret_admin@example.com"
    )
    registered = await async_client.post(
        f"{BASE}/auth/register",
        json={"full_name": "Secret", "email": "onb2_secret@example.com", "password": PASSWORD},
    )
    headers = _bearer(registered.json()["access_token"])

    with caplog.at_level(logging.DEBUG):
        wrong_unit = await async_client.post(
            f"{BASE}/memberships/join",
            json={"code": code, "unit_no": "ZZ-9"},
            headers=headers,
        )
        bad_code = await async_client.post(
            f"{BASE}/memberships/join",
            json={"code": "WRONGCODE2", "unit_no": "A-1"},
            headers=headers,
        )

    assert bad_code.status_code == 404, bad_code.text
    assert wrong_unit.status_code == 404, wrong_unit.text
    assert code not in wrong_unit.text
    assert code not in caplog.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_another_estate_admin_cannot_touch_this_estate(db_session, async_client) -> None:
    outsider_headers, outsider_code, outsider_estate_id, _ = await _new_estate_world(
        async_client,
        name="Onb2 Outsider Estate",
        email="onb2_outsider@example.com",
        unit_nos=("O-1",),
    )
    our_admin, code, estate_id, unit_ids = await _new_estate_world(
        async_client, name="Onb2 Sweep Estate", email="onb2_sweep_admin@example.com", unit_nos=("S-1",)
    )

    # The outsider's own code list, on their own estate, works.
    own = await async_client.get(
        f"{BASE}/join-codes/current?estate_id={outsider_estate_id}", headers=outsider_headers
    )
    assert own.status_code == 200, own.text
    assert own.json()["code"] == outsider_code
    assert own.json()["code"] != code

    sweep = [
        ("get", f"{BASE}/join-codes/current?estate_id={estate_id}", None),
        ("post", f"{BASE}/join-codes?estate_id={estate_id}", {}),
        ("get", f"{BASE}/memberships?estate_id={estate_id}", None),
        (
            "post",
            f"{BASE}/properties/bulk?estate_id={estate_id}",
            {"units": [{"unit_no": "S-9", "street_address": "9 Road"}]},
        ),
    ]
    for method, url, payload in sweep:
        if method == "post":
            response = await async_client.post(url, json=payload, headers=outsider_headers)
        else:
            response = await async_client.get(url, headers=outsider_headers)
        assert response.status_code in (403, 404), (url, response.status_code, response.text)

    # Nothing the outsider attempted landed: our estate still has its one unit.
    listed = await async_client.get(f"{BASE}/memberships?estate_id={estate_id}", headers=our_admin)
    assert listed.json()["total"] == 1
    ours = await async_client.get(f"{BASE}/properties?estate_id={estate_id}", headers=our_admin)
    assert ours.json()["total"] == 1

    # The outsider cannot delete a membership of the other estate either.
    victim = listed.json()["items"][0]["membership_id"]
    removed = await async_client.delete(
        f"{BASE}/memberships/{victim}?estate_id={outsider_estate_id}", headers=outsider_headers
    )
    assert removed.status_code in (403, 404), removed.text
    still_there = await async_client.get(f"{BASE}/memberships?estate_id={estate_id}", headers=our_admin)
    assert still_there.json()["total"] == 1

    # An admin membership cannot be removed at all.
    admin_row = [i for i in listed.json()["items"] if i["role"] == "hoa_admin"][0]["membership_id"]
    refused = await async_client.delete(
        f"{BASE}/memberships/{admin_row}?estate_id={estate_id}", headers=our_admin
    )
    assert refused.status_code == 409, refused.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bulk_units_is_all_or_nothing_on_a_real_duplicate(db_session, async_client) -> None:
    from app.property.repositories.property_repository import PropertyRepository

    admin_headers, _, estate_id, unit_ids = await _new_estate_world(
        async_client, name="Onb2 Bulk Estate", email="onb2_bulk_admin@example.com", unit_nos=("Z-1",)
    )

    clashing = await async_client.post(
        f"{BASE}/properties/bulk?estate_id={estate_id}",
        json={
            "units": [
                {"unit_no": "Z-2", "street_address": "2 Road"},
                {"unit_no": "Z-1", "street_address": "1 Road"},
            ]
        },
        headers=admin_headers,
    )
    assert clashing.status_code == 409, clashing.text
    assert "Z-1" in clashing.json()["detail"]["message"]

    units = await PropertyRepository(db_session).search(offset=0, limit=50, estate_id=estate_id)
    assert sorted(u.unit_no for u in units) == ["Z-1"]
    assert units[0].complex_name == "Onb2 Bulk Estate"
    assert units[0].suburb == "Centurion"

    # Repeating the same unit twice inside one request is also rejected.
    repeated = await async_client.post(
        f"{BASE}/properties/bulk?estate_id={estate_id}",
        json={
            "units": [
                {"unit_no": "Z-3", "street_address": "3 Road"},
                {"unit_no": "Z-3", "street_address": "3 Road again"},
            ]
        },
        headers=admin_headers,
    )
    assert repeated.status_code == 409, repeated.text
    assert (await PropertyRepository(db_session).search(offset=0, limit=50, estate_id=estate_id)).__len__() == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_duplicate_joins_create_one_membership(db_session, async_client) -> None:
    import asyncio

    from app.identity.repositories.estate_membership_repository import (
        EstateMembershipRepository,
    )

    admin_headers, code, estate_id, unit_ids = await _new_estate_world(
        async_client, name="Onb2 Race Estate", email="onb2_race_admin@example.com"
    )
    registered = await async_client.post(
        f"{BASE}/auth/register",
        json={"full_name": "Racer", "email": "onb2_race@example.com", "password": PASSWORD},
    )
    headers = _bearer(registered.json()["access_token"])
    user_id = registered.json()["user"]["id"]

    responses = await asyncio.gather(
        *[
            async_client.post(
                f"{BASE}/memberships/join",
                json={"code": code, "unit_no": "A-1"},
                headers=headers,
            )
            for _ in range(2)
        ]
    )
    statuses = sorted(r.status_code for r in responses)
    assert statuses[0] in (201, 409), [r.text for r in responses]
    assert statuses[1] in (201, 409), [r.text for r in responses]
    assert 201 in statuses

    memberships = await EstateMembershipRepository(db_session).list_for_user(user_id=user_id)
    assert len(memberships) == 1
    assert memberships[0].estate_id == estate_id
    assert memberships[0].property_id == unit_ids[0]
    assert memberships[0].membership_role == "resident"
