"""ONB-1 — role-aware signup, estate registration and re-scoping of role-only endpoints.

Two layers, following ``test_announcements_estate_scoping.py``:

* **Policy / DTO / service tests** run everywhere without a database. They pin the
  signup contract, the platform-admin guard on provider writes, and the estate
  membership rule for listing and sale writes.
* **Integration tests** (``@pytest.mark.integration``) carry every claim that needs
  persisted rows to be meaningful - the one-transaction signup, the cross-estate
  sweep and the log redaction. They auto-skip when ``TEST_DATABASE_URL`` is unset.
"""
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from tests.operator_fixtures import signup_fixture
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.api.router import create_api_router
from app.common.enums import UserRole
from app.core.exceptions import ConflictException, ForbiddenException
from app.db.session import get_db
from app.identity.api.dependencies import get_current_user
from app.identity.schemas.auth import (
    AuthResponse,
    EstateRegistrationRequest,
    ProvisionAccountRequest,
    UserResponse,
)
from app.identity.services.auth_service import AuthService
from app.providers.services.service_provider_service import ServiceProviderService
from app.property.schemas.listing import ListingCreate, ListingUpdate
from app.property.schemas.sale import SaleCreate
from app.property.services.listing_service import ListingService
from app.property.services.sale_service import SaleService

from app.main import app

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import assign_platform_admin as opa  # noqa: E402

client = TestClient(app)

PASSWORD = "correct-horse-battery-staple"


def _register_body(**overrides) -> dict:
    body = {
        "full_name": "Nandi Dlamini",
        "email": "nandi@example.com",
        "password": PASSWORD,
    }
    body.update(overrides)
    return body


# --------------------------------------------------------------------------- #
# 1. The public signup contract
# --------------------------------------------------------------------------- #
def test_role_field_is_still_rejected() -> None:
    with pytest.raises(ValidationError):
        ProvisionAccountRequest.model_validate(
            _register_body(role=UserRole.hoa_admin.value)
        )


def test_unknown_account_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ProvisionAccountRequest.model_validate(_register_body(account_type="superuser"))


def test_platform_admin_is_not_a_self_selectable_account_type() -> None:
    with pytest.raises(ValidationError):
        ProvisionAccountRequest.model_validate(_register_body(account_type="platform_admin"))


def test_estate_agent_and_investor_are_not_self_selectable() -> None:
    for account_type in ("estate_agent", "investor"):
        with pytest.raises(ValidationError):
            ProvisionAccountRequest.model_validate(_register_body(account_type=account_type))


def test_estate_admin_requires_an_estate_object() -> None:
    with pytest.raises(ValidationError):
        ProvisionAccountRequest.model_validate(_register_body(account_type="estate_admin"))


def test_service_provider_requires_a_provider_object() -> None:
    with pytest.raises(ValidationError):
        ProvisionAccountRequest.model_validate(_register_body(account_type="service_provider"))


def test_resident_must_not_supply_estate_or_provider() -> None:
    with pytest.raises(ValidationError):
        ProvisionAccountRequest.model_validate(
            _register_body(
                account_type="resident",
                estate={"name": "X", "suburb": "Y", "city": "Z", "province": "GP"},
            )
        )
    with pytest.raises(ValidationError):
        ProvisionAccountRequest.model_validate(
            _register_body(account_type="resident", provider={"trade": "plumbing", "phone": "082"})
        )


def test_operator_provision_body_accepts_estate_and_defaults_to_resident() -> None:
    assert ProvisionAccountRequest.model_validate(_register_body()).account_type == "resident"

    payload = ProvisionAccountRequest.model_validate(
        _register_body(
            account_type="estate_admin",
            estate={
                "name": "Amberfield Valley",
                "suburb": "Centurion",
                "city": "Pretoria",
                "province": "Gauteng",
            },
        )
    )
    assert payload.estate is not None and payload.estate.name == "Amberfield Valley"


def test_public_estate_registration_does_not_accept_role_or_existing_estate() -> None:
    payload = EstateRegistrationRequest.model_validate(
        _register_body(
            estate={
                "name": "Amberfield Valley",
                "suburb": "Centurion",
                "city": "Pretoria",
                "province": "Gauteng",
            },
        )
    )
    assert payload.estate.name == "Amberfield Valley"

    for extra in ({"role": "hoa_admin"}, {"account_type": "estate_admin"}, {"estate_id": 1}):
        with pytest.raises(ValidationError):
            EstateRegistrationRequest.model_validate(
                _register_body(
                    estate={
                        "name": "Amberfield Valley",
                        "suburb": "Centurion",
                        "city": "Pretoria",
                        "province": "Gauteng",
                    },
                    **extra,
                )
            )


# --------------------------------------------------------------------------- #
# 2. Provider writes require platform_admin
# --------------------------------------------------------------------------- #
def _route_client(*, role: str = "hoa_admin", enable_legacy: bool = True) -> TestClient:
    test_app = FastAPI()
    test_app.include_router(create_api_router(enable_legacy))
    test_app.dependency_overrides[get_db] = lambda: object()
    test_app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        user_id=7, role=role
    )
    return TestClient(test_app)


def test_provider_creation_is_denied_for_every_non_platform_role() -> None:
    body = {
        "full_name": "Provider One",
        "trade": "plumbing",
        "phone": "0821234567",
        "email": "provider@example.com",
    }
    for role in ("hoa_admin", "resident", "service_provider", "estate_agent"):
        assert _route_client(role=role).post("/api/v1/providers", json=body).status_code == 403


def test_provider_update_and_verify_is_denied_for_non_platform_roles() -> None:
    for role in ("hoa_admin", "resident", "service_provider"):
        response = _route_client(role=role).patch(
            "/api/v1/providers/1", json={"verified": True}
        )
        assert response.status_code == 403


def test_platform_admin_can_create_and_update_providers(monkeypatch) -> None:
    from app.providers.schemas.service_provider import ServiceProviderResponse

    provider = ServiceProviderResponse(
        provider_id=1,
        full_name="Provider One",
        trade="plumbing",
        phone="0821234567",
        email="provider@example.com",
        avg_rating=None,
        total_reviews=0,
        verified=False,
        emergency_available=False,
    )
    monkeypatch.setattr(
        ServiceProviderService, "create_provider", AsyncMock(return_value=provider)
    )
    monkeypatch.setattr(
        ServiceProviderService, "update_provider", AsyncMock(return_value=provider)
    )
    admin_client = _route_client(role="platform_admin")

    created = admin_client.post(
        "/api/v1/providers",
        json={
            "full_name": "Provider One",
            "trade": "plumbing",
            "phone": "0821234567",
            "email": "provider@example.com",
        },
    )
    updated = admin_client.patch("/api/v1/providers/1", json={"verified": True})

    assert created.status_code == 201, created.text
    assert updated.status_code == 200, updated.text


def test_public_estate_registration_routes_to_its_dedicated_service(monkeypatch) -> None:
    response_body = AuthResponse(
        access_token="test-access-token",
        user=UserResponse(
            user_id=11,
            email="nandi@example.com",
            full_name="Nandi Dlamini",
            role=UserRole.hoa_admin.value,
            unit_no=None,
            email_verified=False,
            hoa_approved=False,
        ),
    )
    register_estate = AsyncMock(return_value=response_body)
    monkeypatch.setattr(AuthService, "register_estate", register_estate)

    response = _route_client().post(
        "/api/v1/auth/register-estate",
        json=_register_body(
            estate={
                "name": "Amberfield Valley",
                "suburb": "Centurion",
                "city": "Pretoria",
                "province": "Gauteng",
            },
        ),
    )

    assert response.status_code == 201, response.text
    assert response.json()["user"]["role"] == UserRole.hoa_admin.value
    payload = register_estate.await_args.args[0]
    assert isinstance(payload, EstateRegistrationRequest)
    assert payload.estate.name == "Amberfield Valley"


# --------------------------------------------------------------------------- #
# 3. Listing writes: hoa_admin is scoped to an estate they administer
# --------------------------------------------------------------------------- #
def _listing_row(**overrides):
    row = {
        "listing_id": 1,
        "unit_id": 10,
        "agent_id": 99,
        "price": Decimal("1000000.00"),
        "description": None,
        "photo_url": None,
        "status": "active",
        "views": 0,
        "created_at": datetime.now(timezone.utc),
        "updated_at": None,
    }
    row.update(overrides)
    return SimpleNamespace(**row)


class FakeAuthorization:
    def __init__(self, *, allowed_estate_ids=(), is_admin=True):
        self.allowed = set(allowed_estate_ids)
        self.is_admin = is_admin
        self.calls: list[int | None] = []

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


class FakePropertyRepo:
    def __init__(self, property_):
        self._property = property_

    async def get_by_id(self, unit_id):
        return self._property


class FakeListingRepo:
    def __init__(self, *, existing=None):
        self.created: dict | None = None
        self.updated: dict | None = None
        self._existing = existing

    async def create(self, **kwargs):
        self.created = kwargs
        return _listing_row(unit_id=kwargs["unit_id"], agent_id=kwargs["agent_id"])

    async def get_by_id(self, listing_id):
        return self._existing

    async def update(self, listing, changes):
        self.updated = changes
        for key, value in changes.items():
            setattr(listing, key, value)
        return listing


def _listing_service(monkeypatch, *, estate_id, fake_repo, auth):
    import app.property.services.listing_service as module

    property_ = SimpleNamespace(unit_id=10, estate_id=estate_id)
    monkeypatch.setattr(module, "ListingRepository", lambda _db: fake_repo)
    monkeypatch.setattr(module, "PropertyRepository", lambda _db: FakePropertyRepo(property_))
    monkeypatch.setattr(module, "EstateAuthorizationService", lambda _db: auth)
    return ListingService(object())


@pytest.mark.asyncio
async def test_hoa_admin_cannot_create_a_listing_for_a_foreign_estate(monkeypatch) -> None:
    repo = FakeListingRepo()
    service = _listing_service(monkeypatch, estate_id=99, fake_repo=repo, auth=FakeAuthorization())
    actor = SimpleNamespace(user_id=7, role=UserRole.hoa_admin.value)

    with pytest.raises(ForbiddenException):
        await service.create_listing(
            ListingCreate(unit_id=10, price=Decimal("1000.00")), actor
        )
    assert repo.created is None


@pytest.mark.asyncio
async def test_hoa_admin_cannot_create_a_listing_for_a_legacy_null_estate(monkeypatch) -> None:
    repo = FakeListingRepo()
    auth = FakeAuthorization(allowed_estate_ids={1})
    service = _listing_service(monkeypatch, estate_id=None, fake_repo=repo, auth=auth)
    actor = SimpleNamespace(user_id=7, role=UserRole.hoa_admin.value)

    with pytest.raises(ForbiddenException):
        await service.create_listing(
            ListingCreate(unit_id=10, price=Decimal("1000.00")), actor
        )
    assert auth.calls == []  # a NULL-estate unit is denied before any membership lookup
    assert repo.created is None


@pytest.mark.asyncio
async def test_hoa_admin_can_create_a_listing_inside_their_estate(monkeypatch) -> None:
    repo = FakeListingRepo()
    auth = FakeAuthorization(allowed_estate_ids={1})
    service = _listing_service(monkeypatch, estate_id=1, fake_repo=repo, auth=auth)
    actor = SimpleNamespace(user_id=7, role=UserRole.hoa_admin.value)

    await service.create_listing(ListingCreate(unit_id=10, price=Decimal("1000.00")), actor)

    assert repo.created is not None
    assert repo.created["agent_id"] == 7


@pytest.mark.asyncio
async def test_estate_agent_listing_creation_is_unchanged(monkeypatch) -> None:
    repo = FakeListingRepo()
    auth = FakeAuthorization()
    service = _listing_service(monkeypatch, estate_id=99, fake_repo=repo, auth=auth)
    actor = SimpleNamespace(user_id=7, role=UserRole.estate_agent.value)

    await service.create_listing(ListingCreate(unit_id=10, price=Decimal("1000.00")), actor)

    assert repo.created is not None
    assert auth.calls == []  # an agent carries no estate membership requirement


@pytest.mark.asyncio
async def test_hoa_admin_cannot_edit_a_listing_outside_their_estate(monkeypatch) -> None:
    existing = _listing_row(agent_id=99, unit_id=10)
    repo = FakeListingRepo(existing=existing)
    service = _listing_service(monkeypatch, estate_id=99, fake_repo=repo, auth=FakeAuthorization())
    actor = SimpleNamespace(user_id=7, role=UserRole.hoa_admin.value)

    with pytest.raises(ForbiddenException):
        await service.update_listing(1, ListingUpdate(price=Decimal("2000.00")), actor)
    assert repo.updated is None


@pytest.mark.asyncio
async def test_hoa_admin_can_edit_a_listing_inside_their_estate(monkeypatch) -> None:
    existing = _listing_row(agent_id=99, unit_id=10)
    repo = FakeListingRepo(existing=existing)
    auth = FakeAuthorization(allowed_estate_ids={1})
    service = _listing_service(monkeypatch, estate_id=1, fake_repo=repo, auth=auth)
    actor = SimpleNamespace(user_id=7, role=UserRole.hoa_admin.value)

    await service.update_listing(1, ListingUpdate(price=Decimal("2000.00")), actor)

    assert repo.updated == {"price": Decimal("2000.00")}


@pytest.mark.asyncio
async def test_estate_agent_cannot_edit_someone_elses_listing(monkeypatch) -> None:
    existing = _listing_row(agent_id=99, unit_id=10)
    repo = FakeListingRepo(existing=existing)
    auth = FakeAuthorization(allowed_estate_ids={1})
    service = _listing_service(monkeypatch, estate_id=1, fake_repo=repo, auth=auth)
    actor = SimpleNamespace(user_id=7, role=UserRole.estate_agent.value)

    with pytest.raises(ForbiddenException):
        await service.update_listing(1, ListingUpdate(price=Decimal("2000.00")), actor)
    assert repo.updated is None
    assert auth.calls == []


# --------------------------------------------------------------------------- #
# 4. Sale writes: hoa_admin is scoped to an estate they administer
# --------------------------------------------------------------------------- #
def _sale_row(**overrides):
    row = {
        "sale_id": 1,
        "unit_id": 10,
        "price": Decimal("1000000.00"),
        "sale_date": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
    }
    row.update(overrides)
    return SimpleNamespace(**row)


class FakeSaleRepo:
    def __init__(self):
        self.created: dict | None = None

    async def create(self, **kwargs):
        self.created = kwargs
        return _sale_row(**kwargs)


def _sale_service(monkeypatch, *, estate_id, repo, auth):
    import app.property.services.sale_service as module

    property_ = SimpleNamespace(unit_id=10, estate_id=estate_id)
    monkeypatch.setattr(module, "SaleRepository", lambda _db: repo)
    monkeypatch.setattr(module, "PropertyRepository", lambda _db: FakePropertyRepo(property_))
    monkeypatch.setattr(module, "EstateAuthorizationService", lambda _db: auth)
    return SaleService(object())


def _sale_payload() -> SaleCreate:
    return SaleCreate(
        unit_id=10, price=Decimal("1000000.00"), sale_date=datetime.now(timezone.utc)
    )


@pytest.mark.asyncio
async def test_hoa_admin_cannot_create_a_sale_for_a_foreign_estate(monkeypatch) -> None:
    repo = FakeSaleRepo()
    service = _sale_service(monkeypatch, estate_id=99, repo=repo, auth=FakeAuthorization())
    actor = SimpleNamespace(user_id=7, role=UserRole.hoa_admin.value)

    with pytest.raises(ForbiddenException):
        await service.create_sale(_sale_payload(), actor)
    assert repo.created is None


@pytest.mark.asyncio
async def test_hoa_admin_cannot_create_a_sale_for_a_legacy_null_estate(monkeypatch) -> None:
    repo = FakeSaleRepo()
    auth = FakeAuthorization(allowed_estate_ids={1})
    service = _sale_service(monkeypatch, estate_id=None, repo=repo, auth=auth)
    actor = SimpleNamespace(user_id=7, role=UserRole.hoa_admin.value)

    with pytest.raises(ForbiddenException):
        await service.create_sale(_sale_payload(), actor)
    assert auth.calls == []
    assert repo.created is None


@pytest.mark.asyncio
async def test_hoa_admin_can_create_a_sale_inside_their_estate(monkeypatch) -> None:
    repo = FakeSaleRepo()
    auth = FakeAuthorization(allowed_estate_ids={1})
    service = _sale_service(monkeypatch, estate_id=1, repo=repo, auth=auth)
    actor = SimpleNamespace(user_id=7, role=UserRole.hoa_admin.value)

    await service.create_sale(_sale_payload(), actor)

    assert repo.created is not None


@pytest.mark.asyncio
async def test_estate_agent_sale_creation_is_unchanged(monkeypatch) -> None:
    repo = FakeSaleRepo()
    auth = FakeAuthorization()
    service = _sale_service(monkeypatch, estate_id=99, repo=repo, auth=auth)
    actor = SimpleNamespace(user_id=7, role=UserRole.estate_agent.value)

    await service.create_sale(_sale_payload(), actor)
    assert repo.created is not None


# --------------------------------------------------------------------------- #
# 5. Signup orchestration: exactly one transaction per account type
# --------------------------------------------------------------------------- #
class FakeSession:
    def __init__(self, *, fail_commit: bool = False):
        self.commits = 0
        self.rollbacks = 0
        self._fail_commit = fail_commit

    async def commit(self):
        if self._fail_commit:
            raise IntegrityError("stmt", {}, Exception("duplicate key"))
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1

    async def refresh(self, _obj):
        return None


class FakeUserRepo:
    def __init__(self, *, existing=None):
        self.created: dict | None = None
        self.add_calls = 0
        self._existing = existing

    async def get_by_email(self, email):
        return self._existing

    def _row(self, fields):
        return SimpleNamespace(
            user_id=11,
            email=fields["email"],
            full_name=fields["full_name"],
            role=fields["role"],
            unit_no=fields.get("unit_no"),
            email_verified=False,
            hoa_approved=False,
        )

    async def add(self, **fields):
        self.add_calls += 1
        self.created = fields
        return self._row(fields)

    async def create(self, **fields):
        self.add_calls += 1
        self.created = fields
        return self._row(fields)


class FakeEstateRepo:
    def __init__(self, *, name_exists=False):
        self.added: dict | None = None
        self.get_by_name_calls = 0
        self._name_exists = name_exists

    async def get_by_name(self, name):
        self.get_by_name_calls += 1
        if self._name_exists:
            return SimpleNamespace(estate_id=5, name=name)
        return None

    async def add(self, **fields):
        self.added = fields
        return SimpleNamespace(estate_id=5, **fields)


class FakeMembershipRepo:
    def __init__(self, *, explode=False):
        self.added: dict | None = None
        self._explode = explode

    async def add(self, **fields):
        if self._explode:
            raise AssertionError("no membership may be created for this account type")
        self.added = fields
        return SimpleNamespace(membership_id=1, **fields)


class FakeProviderRepo:
    def __init__(self):
        self.added: dict | None = None

    async def get_by_email(self, email):
        return None

    async def add(self, **fields):
        self.added = fields
        return SimpleNamespace(provider_id=1, **fields)


def _auth_service(*, session, user_repo, estate_repo, membership_repo, provider_repo):
    service = AuthService.__new__(AuthService)
    service._db = session
    service._repo = user_repo
    service._estate_repo = estate_repo
    service._membership_repo = membership_repo
    service._provider_repo = provider_repo
    return service


@pytest.mark.asyncio
async def test_estate_admin_signup_creates_user_estate_and_membership_once() -> None:
    session = FakeSession()
    user_repo = FakeUserRepo()
    estate_repo = FakeEstateRepo()
    membership_repo = FakeMembershipRepo()
    service = _auth_service(
        session=session,
        user_repo=user_repo,
        estate_repo=estate_repo,
        membership_repo=membership_repo,
        provider_repo=FakeProviderRepo(),
    )

    response = await service.register_estate(
        EstateRegistrationRequest.model_validate(
            _register_body(
                estate={
                    "name": "Amberfield Valley",
                    "suburb": "Centurion",
                    "city": "Pretoria",
                    "province": "Gauteng",
                    "description": "New estate",
                },
            )
        )
    )

    assert session.commits == 1
    assert session.rollbacks == 0
    assert user_repo.created is not None
    assert user_repo.created["role"] == UserRole.hoa_admin.value
    assert estate_repo.added is not None
    assert estate_repo.added["is_demo"] is False
    assert estate_repo.added["is_public"] is False
    assert estate_repo.added["name"] == "Amberfield Valley"
    assert membership_repo.added == {
        "user_id": 11,
        "estate_id": 5,
        "property_id": None,
        "membership_role": UserRole.hoa_admin.value,
    }
    assert response.user.role == UserRole.hoa_admin.value


@pytest.mark.asyncio
async def test_duplicate_estate_name_creates_no_user_and_writes_nothing() -> None:
    session = FakeSession()
    user_repo = FakeUserRepo()
    service = _auth_service(
        session=session,
        user_repo=user_repo,
        estate_repo=FakeEstateRepo(name_exists=True),
        membership_repo=FakeMembershipRepo(),
        provider_repo=FakeProviderRepo(),
    )

    with pytest.raises(ConflictException):
        await service._create_account(
            ProvisionAccountRequest.model_validate(
                _register_body(
                    account_type="estate_admin",
                    estate={
                        "name": "Amberfield Valley",
                        "suburb": "Centurion",
                        "city": "Pretoria",
                        "province": "Gauteng",
                    },
                )
            )
        )

    assert session.commits == 0
    assert user_repo.add_calls == 0


@pytest.mark.asyncio
async def test_failed_commit_on_estate_signup_rolls_back() -> None:
    session = FakeSession(fail_commit=True)
    user_repo = FakeUserRepo()
    service = _auth_service(
        session=session,
        user_repo=user_repo,
        estate_repo=FakeEstateRepo(),
        membership_repo=FakeMembershipRepo(),
        provider_repo=FakeProviderRepo(),
    )

    with pytest.raises(ConflictException):
        await service._create_account(
            ProvisionAccountRequest.model_validate(
                _register_body(
                    account_type="estate_admin",
                    estate={
                        "name": "Amberfield Valley",
                        "suburb": "Centurion",
                        "city": "Pretoria",
                        "province": "Gauteng",
                    },
                )
            )
        )

    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_service_provider_signup_creates_a_linked_profile_with_no_membership() -> None:
    session = FakeSession()
    user_repo = FakeUserRepo()
    provider_repo = FakeProviderRepo()
    service = _auth_service(
        session=session,
        user_repo=user_repo,
        estate_repo=FakeEstateRepo(),
        membership_repo=FakeMembershipRepo(explode=True),
        provider_repo=provider_repo,
    )

    response = await service._create_account(
        ProvisionAccountRequest.model_validate(
            _register_body(account_type="service_provider", provider={"trade": "plumbing", "phone": "0821234567"})
        )
    )

    assert session.commits == 1
    assert user_repo.created is not None
    assert user_repo.created["role"] == UserRole.service_provider.value
    assert provider_repo.added is not None
    assert provider_repo.added["user_id"] == 11
    assert provider_repo.added["email"] == "nandi@example.com"
    assert provider_repo.added["trade"] == "plumbing"
    assert provider_repo.added["phone"] == "0821234567"
    assert provider_repo.added["verified"] is False
    assert provider_repo.added["emergency_available"] is False
    assert response.user.role == UserRole.service_provider.value


@pytest.mark.asyncio
async def test_resident_signup_is_unchanged() -> None:
    session = FakeSession()
    user_repo = FakeUserRepo()
    service = _auth_service(
        session=session,
        user_repo=user_repo,
        estate_repo=FakeEstateRepo(),
        membership_repo=FakeMembershipRepo(explode=True),
        provider_repo=FakeProviderRepo(),
    )

    response = await service._create_account(ProvisionAccountRequest.model_validate(_register_body()))

    assert user_repo.created is not None
    assert user_repo.created["role"] == UserRole.resident.value
    assert response.user.role == UserRole.resident.value


# --------------------------------------------------------------------------- #
# 6. Integration: real database only. Auto-skip without TEST_DATABASE_URL.
# --------------------------------------------------------------------------- #
def _bearer_token(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _estate_admin_body(*, email: str, estate_name: str) -> dict:
    return _register_body(
        email=email,
        estate={
            "name": estate_name,
            "suburb": "Centurion",
            "city": "Pretoria",
            "province": "Gauteng",
            "description": "Registered during ONB-1 tests",
        },
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_estate_admin_signup_creates_estate_and_membership_then_lists_it(
    db_session, async_client
) -> None:
    from app.identity.repositories.estate_membership_repository import (
        EstateMembershipRepository,
    )
    from app.property.repositories.estate_repository import EstateRepository

    response = await signup_fixture(async_client,
        "/api/v1/auth/register-estate",
        json=_estate_admin_body(
            email="onb_estate_admin@example.com", estate_name="Onboarding Test Estate"
        ),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["role"] == "hoa_admin"
    user_id = body["user"]["id"]

    estate = await EstateRepository(db_session).get_by_name("Onboarding Test Estate")
    assert estate is not None
    assert estate.is_demo is False
    assert estate.is_public is False

    memberships = await EstateMembershipRepository(db_session).list_for_user(user_id=user_id)
    assert len(memberships) == 1
    assert memberships[0].estate_id == estate.estate_id
    assert memberships[0].property_id is None
    assert memberships[0].membership_role == "hoa_admin"

    estates = await async_client.get(
        "/api/v1/auth/estates", headers=_bearer_token(body["access_token"])
    )
    assert estates.status_code == 200, estates.text
    assert "Onboarding Test Estate" in [
        item["estate_name"] for item in estates.json()["estates"]
    ]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_duplicate_estate_name_rolls_back_the_whole_signup(db_session, async_client) -> None:
    from app.identity.repositories.user_repository import UserRepository
    from app.property.repositories.estate_repository import EstateRepository

    first = await signup_fixture(async_client,
        "/api/v1/auth/register-estate",
        json=_estate_admin_body(email="onb_dup_first@example.com", estate_name="Duplicate Estate"),
    )
    assert first.status_code == 201, first.text

    second = await signup_fixture(async_client,
        "/api/v1/auth/register-estate",
        json=_estate_admin_body(email="onb_dup_second@example.com", estate_name="Duplicate Estate"),
    )
    assert second.status_code == 409, second.text

    # No orphan user is left behind for the rejected attempt.
    assert await UserRepository(db_session).get_by_email("onb_dup_second@example.com") is None
    assert (await EstateRepository(db_session).get_by_name("Duplicate Estate")) is not None


_ESTATE_SCOPED_SWEEP = [
    ("get", "/api/v1/complaints", None),
    ("get", "/api/v1/complaints/stats", None),
    ("get", "/api/v1/announcements", None),
    ("get", "/api/v1/incidents", None),
    ("get", "/api/v1/properties", None),
    ("get", "/api/v1/work-orders", None),
    (
        "post",
        "/api/v1/complaints",
        {"unit_id": 1, "category": "other", "description": "Cross estate attempt"},
    ),
    ("post", "/api/v1/announcements", {"title": "Cross", "message": "Cross estate"}),
    (
        "post",
        "/api/v1/incidents",
        {
            "category": "other",
            "severity": "low",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        },
    ),
    ("post", "/api/v1/work-orders", {"complaint_id": 1, "provider_id": 1}),
]


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("method,path,body", _ESTATE_SCOPED_SWEEP)
async def test_new_estate_admin_gets_403_or_404_on_another_estate(
    db_session, async_client, method, path, body
) -> None:
    from tests.factories import build_two_estate_world

    world = await build_two_estate_world(db_session)
    registration = await signup_fixture(async_client,
        "/api/v1/auth/register-estate",
        json=_estate_admin_body(email="onb_sweep@example.com", estate_name="Sweep Estate"),
    )
    assert registration.status_code == 201, registration.text
    headers = _bearer_token(registration.json()["access_token"])

    url = f"{path}?estate_id={world.estate_a.estate_id}"
    # httpx's get() takes no JSON body; only the POST variants carry one.
    if method == "post":
        response = await async_client.post(url, json=body, headers=headers)
    else:
        response = await async_client.get(url, headers=headers)

    assert response.status_code in (403, 404), (
        method,
        url,
        response.status_code,
        response.text,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_public_provider_signup_is_rejected(
    db_session, async_client
) -> None:
    from app.providers.repositories.service_provider_repository import (
        ServiceProviderRepository,
    )

    # Do not use signup_fixture here: it deliberately routes trusted provider
    # provisioning payloads through /auth/provision. Exercise the public route
    # directly to prove that clients cannot self-select the service_provider role.
    response = await async_client.post(
        "/api/v1/auth/register",
        json=_register_body(
            account_type="service_provider",
            email="onb_provider@example.com",
            provider={"trade": "plumbing", "phone": "0821234567"},
        ),
    )
    assert response.status_code == 422, response.text

    profile = await ServiceProviderRepository(db_session).get_by_email(
        "onb_provider@example.com"
    )
    assert profile is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_platform_admin_cannot_be_obtained_through_any_public_endpoint(async_client) -> None:
    as_account_type = await signup_fixture(async_client,
        "/api/v1/auth/register",
        json=_register_body(account_type="platform_admin"),
    )
    as_role_field = await signup_fixture(async_client,
        "/api/v1/auth/register",
        json=_register_body(role="platform_admin"),
    )

    assert as_account_type.status_code == 422
    assert as_role_field.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_password_never_appears_in_the_logs(async_client, caplog) -> None:
    secret = "onb1-unique-password-do-not-log-9f3c"
    with caplog.at_level(logging.DEBUG):
        response = await signup_fixture(async_client,
            "/api/v1/auth/register",
            json=_register_body(
                email="onb_logs@example.com",
                password=secret,
            ),
        )
    assert response.status_code == 201, response.text
    assert secret not in caplog.text


# --------------------------------------------------------------------------- #
# 7. The operator CLI: platform_admin is granted only here
# --------------------------------------------------------------------------- #
class _OperatorResult:
    def __init__(self, user):
        self._user = user

    def scalar_one_or_none(self):
        return self._user


class OperatorSession:
    def __init__(self, user):
        self._user = user
        self.commits = 0

    async def execute(self, _stmt):
        return _OperatorResult(self._user)

    async def commit(self):
        self.commits += 1


def _operator_factory(session):
    @asynccontextmanager
    async def factory():
        yield session

    return factory


def _operator(role: str = "resident"):
    return SimpleNamespace(user_id=42, email="ops@example.com", role=role)


@pytest.mark.asyncio
async def test_operator_cli_dry_run_does_not_change_the_role() -> None:
    user = _operator()
    session = OperatorSession(user)

    code = await opa.main(
        ["--email", "ops@example.com"], session_factory=_operator_factory(session)
    )

    assert code == 0
    assert user.role == "resident"
    assert session.commits == 0


@pytest.mark.asyncio
async def test_operator_cli_apply_promotes_the_account(monkeypatch) -> None:
    # This CLI unit test injects a fake session; its safety context must not
    # depend on the real integration suite's guarded demo database name.
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/valora_operator_test")
    user = _operator()
    session = OperatorSession(user)

    code = await opa.main(
        ["--email", "ops@example.com", "--apply"],
        session_factory=_operator_factory(session),
    )

    assert code == 0
    assert user.role == UserRole.platform_admin.value
    assert session.commits == 1


@pytest.mark.asyncio
async def test_operator_cli_missing_account_is_an_error(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/valora_operator_test")
    session = OperatorSession(None)

    code = await opa.main(
        ["--email", "nobody@example.com", "--apply"],
        session_factory=_operator_factory(session),
    )

    assert code == 1
    assert session.commits == 0


@pytest.mark.asyncio
async def test_operator_cli_refuses_a_demo_database(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/valora_demo")
    user = _operator()
    session = OperatorSession(user)

    code = await opa.main(
        ["--email", "ops@example.com", "--apply"],
        session_factory=_operator_factory(session),
    )

    assert code == 1
    assert session.commits == 0


def test_operator_cli_target_url_is_never_read_from_dotenv(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(opa.OperatorError):
        opa.target_database_url()


def test_operator_cli_redacts_credentials() -> None:
    assert "secret" not in opa.redact_database_url(
        "postgresql+asyncpg://user:secret@db.internal:5432/valora"
    )
