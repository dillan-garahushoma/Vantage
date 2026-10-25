from __future__ import annotations

import hashlib
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.common.datetime_utils import utcnow
from app.core.exceptions import ConflictException, NotFoundException
from app.identity.schemas.provider_invitation import (
    ProviderInvitationAcceptRequest,
    ProviderApplicationCreateRequest,
)
from app.identity.services import provider_application_service as application_module
from app.identity.services.provider_application_service import ProviderApplicationService
from app.notifications.email import EmailMessage, NullEmailSender


class FakeSession:
    def __init__(self) -> None:
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.refresh = AsyncMock()


class FakeSender:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.messages: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        if self.error is not None:
            raise self.error
        self.messages.append(message)


def application_payload() -> ProviderApplicationCreateRequest:
    return ProviderApplicationCreateRequest.model_validate(
        {
            "estate_id": 12,
            "full_name": "  Kamo Dube ",
            "email": " KAMO@example.co.za ",
            "trade": " plumbing ",
            "phone": " 082 123 4567 ",
        }
    )


def install_create_dependencies(monkeypatch, db, invitation):
    authorization = SimpleNamespace(require_role=AsyncMock())
    users = SimpleNamespace(get_by_email=AsyncMock(return_value=None))
    providers = SimpleNamespace(get_by_email=AsyncMock(return_value=None))
    invitations = SimpleNamespace(
        revoke_active_for_email=AsyncMock(),
        add=AsyncMock(return_value=invitation),
        get_by_token_digest_for_update=AsyncMock(return_value=invitation),
    )
    application = SimpleNamespace(
        application_id=8,
        estate_id=12,
        full_name="Kamo Dube",
        email="kamo@example.co.za",
        trade="plumbing",
        phone="082 123 4567",
        note=None,
        status="pending",
        created_at=utcnow(),
        reviewed_at=None,
    )
    applications = SimpleNamespace(
        has_pending=AsyncMock(return_value=False),
        add=AsyncMock(return_value=application),
        get_by_id_in_estate=AsyncMock(return_value=application),
        save=AsyncMock(return_value=application),
    )
    estates = SimpleNamespace(
        get_by_id=AsyncMock(
            return_value=SimpleNamespace(
                estate_id=12,
                name="Ridge Close Estate",
                is_public=True,
                is_demo=False,
            )
        )
    )
    monkeypatch.setattr(
        application_module,
        "EstateAuthorizationService",
        lambda _db: authorization,
    )
    monkeypatch.setattr(application_module, "UserRepository", lambda _db: users)
    monkeypatch.setattr(
        application_module, "ServiceProviderRepository", lambda _db: providers
    )
    monkeypatch.setattr(
        application_module, "ProviderInvitationRepository", lambda _db: invitations
    )
    monkeypatch.setattr(
        application_module, "ProviderApplicationRepository", lambda _db: applications
    )
    monkeypatch.setattr(application_module, "EstateRepository", lambda _db: estates)
    monkeypatch.setattr(application_module, "EstateMembershipRepository", lambda _db: object())
    monkeypatch.setattr(
        application_module, "EstateMembershipEventRepository", lambda _db: object()
    )
    return authorization, users, providers, invitations, applications


def test_application_contract_normalizes_fields_and_bounds_secrets() -> None:
    payload = application_payload()
    assert payload.full_name == "Kamo Dube"
    assert payload.email == "kamo@example.co.za"
    assert payload.trade == "plumbing"
    assert payload.phone == "082 123 4567"
    assert payload.estate_id == 12

    accepted = ProviderInvitationAcceptRequest(token="x" * 40, password="aGoodPassword1")
    assert accepted.password == "aGoodPassword1"
    with pytest.raises(ValueError):
        ProviderInvitationAcceptRequest(token="short", password="aGoodPassword1")
    with pytest.raises(ValueError):
        ProviderInvitationAcceptRequest(token="x" * 40, password="x" * 73)


@pytest.mark.asyncio
async def test_provider_application_waits_for_hoa_and_does_not_create_account(monkeypatch) -> None:
    db = FakeSession()
    invitation = SimpleNamespace(expires_at=utcnow() + timedelta(days=7))
    _, users, providers, invitations, applications = install_create_dependencies(
        monkeypatch, db, invitation
    )
    service = ProviderApplicationService(db, sender=FakeSender())
    result = await service.apply(application_payload())

    assert result.status == "pending"
    assert result.estate_name == "Ridge Close Estate"
    applications.add.assert_awaited_once()
    assert applications.add.call_args.kwargs["status"] == "pending"
    users.get_by_email.assert_awaited_once_with("kamo@example.co.za")
    providers.get_by_email.assert_awaited_once_with("kamo@example.co.za")
    invitations.add.assert_not_awaited()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("is_public,is_demo", [(False, False), (True, True)])
async def test_provider_application_rejects_estates_not_in_public_directory(
    monkeypatch, is_public: bool, is_demo: bool
) -> None:
    db = FakeSession()
    estate = SimpleNamespace(
        estate_id=12,
        name="Ridge Close Estate",
        is_public=is_public,
        is_demo=is_demo,
    )
    monkeypatch.setattr(
        application_module,
        "EstateRepository",
        lambda _db: SimpleNamespace(get_by_id=AsyncMock(return_value=estate)),
    )

    with pytest.raises(NotFoundException):
        await ProviderApplicationService(db, sender=FakeSender()).apply(application_payload())

    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_hoa_approval_requires_email_and_returns_to_pending_on_delivery_failure(monkeypatch) -> None:
    db = FakeSession()
    invitation = SimpleNamespace(expires_at=utcnow() + timedelta(days=7))
    _, _, _, invitations, applications = install_create_dependencies(
        monkeypatch, db, invitation
    )
    service = ProviderApplicationService(db, sender=NullEmailSender())

    with pytest.raises(HTTPException) as exc_info:
        await service.approve(
            SimpleNamespace(user_id=9, role="hoa_admin"),
            estate_id=12,
            application_id=8,
        )

    assert exc_info.value.status_code == 503
    invitations.add.assert_not_awaited()
    db.commit.assert_not_awaited()

    db = FakeSession()
    _, _, _, invitations, applications = install_create_dependencies(
        monkeypatch, db, invitation
    )
    failed_sender = FakeSender(RuntimeError("relay unavailable"))
    service = ProviderApplicationService(db, sender=failed_sender)
    with pytest.raises(HTTPException) as failed:
        await service.approve(
            SimpleNamespace(user_id=9, role="hoa_admin"),
            estate_id=12,
            application_id=8,
        )
    assert failed.value.status_code == 503
    db.rollback.assert_awaited_once()
    assert db.commit.await_count == 2
    assert applications.save.await_count == 1
    assert applications.get_by_id_in_estate.return_value.status == "pending"
    assert invitations.add.return_value.revoked_at is not None


@pytest.mark.asyncio
async def test_hoa_approval_sends_single_use_setup_link_without_persisting_raw_token(monkeypatch) -> None:
    db = FakeSession()
    invitation = SimpleNamespace(expires_at=utcnow() + timedelta(days=7), revoked_at=None)
    sender = FakeSender()
    _, _, _, invitations, applications = install_create_dependencies(
        monkeypatch, db, invitation
    )
    monkeypatch.setattr(application_module.secrets, "token_urlsafe", lambda _size: "x" * 43)
    service = ProviderApplicationService(db, sender=sender, base_url="https://valora.example/")

    result = await service.approve(
        SimpleNamespace(user_id=9, role="hoa_admin"),
        estate_id=12,
        application_id=8,
    )

    assert result.status == "approved"
    fields = invitations.add.call_args.kwargs
    assert fields["application_id"] == 8
    assert fields["estate_id"] == 12
    assert fields["email"] == "kamo@example.co.za"
    assert fields["token_digest"] == hashlib.sha256(("x" * 43).encode()).hexdigest()
    assert "token" not in fields
    assert "https://valora.example/provider/accept-invitation#token=" + "x" * 43 in sender.messages[0].body
    assert "?token=" not in sender.messages[0].body
    assert "x" * 43 not in result.model_dump_json()
    applications.save.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_acceptance_creates_provider_profile_membership_and_event_once(monkeypatch) -> None:
    db = FakeSession()
    invite = SimpleNamespace(
        invitation_id=3,
        created_by_user_id=9,
        estate_id=12,
        email="kamo@example.co.za",
        full_name="Kamo Dube",
        trade="plumbing",
        phone="082 123 4567",
        expires_at=utcnow() + timedelta(days=1),
        accepted_at=None,
        revoked_at=None,
    )
    invitation_repo = SimpleNamespace(
        get_by_token_digest_for_update=AsyncMock(return_value=invite),
        mark_accepted=AsyncMock(),
    )
    users = SimpleNamespace(
        get_by_email=AsyncMock(return_value=None),
        add=AsyncMock(
            return_value=SimpleNamespace(
                user_id=33,
                email="kamo@example.co.za",
                full_name="Kamo Dube",
                role="service_provider",
                unit_no=None,
                email_verified=False,
                hoa_approved=False,
            )
        ),
    )
    providers = SimpleNamespace(add=AsyncMock())
    memberships = SimpleNamespace(add=AsyncMock())
    events = SimpleNamespace(record=AsyncMock())
    monkeypatch.setattr(
        application_module,
        "ProviderInvitationRepository",
        lambda _db: invitation_repo,
    )
    monkeypatch.setattr(application_module, "UserRepository", lambda _db: users)
    monkeypatch.setattr(
        application_module, "ServiceProviderRepository", lambda _db: providers
    )
    monkeypatch.setattr(
        application_module, "EstateMembershipRepository", lambda _db: memberships
    )
    monkeypatch.setattr(
        application_module, "EstateMembershipEventRepository", lambda _db: events
    )
    monkeypatch.setattr(application_module, "hash_password", lambda _password: "hashed")
    auth_response = object()
    monkeypatch.setattr(
        application_module.AuthService,
        "_build_auth_response",
        staticmethod(lambda _user: auth_response),
    )
    service = ProviderApplicationService(db, sender=FakeSender())

    result = await service.accept(
        ProviderInvitationAcceptRequest(token="x" * 43, password="aGoodPassword1")
    )

    assert result is auth_response
    invitation_repo.get_by_token_digest_for_update.assert_awaited_once_with(
        token_digest=hashlib.sha256(("x" * 43).encode()).hexdigest()
    )
    users.add.assert_awaited_once()
    providers.add.assert_awaited_once()
    memberships.add.assert_awaited_once_with(
        user_id=33,
        estate_id=12,
        property_id=None,
        membership_role="service_provider",
    )
    events.record.assert_awaited_once()
    invitation_repo.mark_accepted.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_acceptance_rejects_used_or_expired_invitation_without_creating_account(monkeypatch) -> None:
    db = FakeSession()
    invite = SimpleNamespace(
        estate_id=12,
        expires_at=utcnow() - timedelta(seconds=1),
        accepted_at=None,
        revoked_at=None,
    )
    invitation_repo = SimpleNamespace(
        get_by_token_digest_for_update=AsyncMock(return_value=invite)
    )
    users = SimpleNamespace(get_by_email=AsyncMock())
    monkeypatch.setattr(
        application_module,
        "ProviderInvitationRepository",
        lambda _db: invitation_repo,
    )
    monkeypatch.setattr(application_module, "UserRepository", lambda _db: users)
    service = ProviderApplicationService(db, sender=FakeSender())

    with pytest.raises(NotFoundException):
        await service.accept(
            ProviderInvitationAcceptRequest(token="x" * 43, password="aGoodPassword1")
        )

    users.get_by_email.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_acceptance_rejects_email_already_used_by_another_account(monkeypatch) -> None:
    db = FakeSession()
    invite = SimpleNamespace(
        estate_id=12,
        email="kamo@example.co.za",
        expires_at=utcnow() + timedelta(days=1),
        accepted_at=None,
        revoked_at=None,
    )
    invitation_repo = SimpleNamespace(
        get_by_token_digest_for_update=AsyncMock(return_value=invite)
    )
    users = SimpleNamespace(
        get_by_email=AsyncMock(return_value=SimpleNamespace(user_id=22, role="resident"))
    )
    providers = SimpleNamespace(get_by_user_id=AsyncMock(return_value=None))
    memberships = SimpleNamespace(has_estate_access=AsyncMock(return_value=False))
    monkeypatch.setattr(
        application_module,
        "ProviderInvitationRepository",
        lambda _db: invitation_repo,
    )
    monkeypatch.setattr(application_module, "UserRepository", lambda _db: users)
    monkeypatch.setattr(
        application_module, "ServiceProviderRepository", lambda _db: providers
    )
    monkeypatch.setattr(
        application_module, "EstateMembershipRepository", lambda _db: memberships
    )
    service = ProviderApplicationService(db, sender=FakeSender())

    with pytest.raises(ConflictException):
        await service.accept(
            ProviderInvitationAcceptRequest(token="x" * 43, password="aGoodPassword1")
        )

    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_existing_provider_can_apply_for_another_estate(monkeypatch) -> None:
    db = FakeSession()
    invitation = SimpleNamespace(expires_at=utcnow() + timedelta(days=7))
    _, users, providers, _, applications = install_create_dependencies(
        monkeypatch, db, invitation
    )
    user = SimpleNamespace(user_id=33, role="service_provider")
    providers.get_by_email.return_value = SimpleNamespace(user_id=33)
    users.get_by_email.return_value = user
    memberships = SimpleNamespace(has_estate_access=AsyncMock(return_value=False))
    monkeypatch.setattr(
        application_module, "EstateMembershipRepository", lambda _db: memberships
    )

    result = await ProviderApplicationService(db, sender=FakeSender()).apply(
        application_payload()
    )

    assert result.status == "pending"
    applications.add.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_existing_provider_joins_another_estate_without_resetting_password(
    monkeypatch,
) -> None:
    db = FakeSession()
    invite = SimpleNamespace(
        invitation_id=3,
        created_by_user_id=9,
        estate_id=12,
        email="kamo@example.co.za",
        full_name="Kamo Dube",
        trade="plumbing",
        phone="082 123 4567",
        expires_at=utcnow() + timedelta(days=1),
        accepted_at=None,
        revoked_at=None,
    )
    provider_user = SimpleNamespace(
        user_id=33,
        email="kamo@example.co.za",
        full_name="Kamo Dube",
        role="service_provider",
    )
    provider_profile = SimpleNamespace(user_id=33)
    invitation_repo = SimpleNamespace(
        get_by_token_digest_for_update=AsyncMock(return_value=invite),
        mark_accepted=AsyncMock(),
    )
    users = SimpleNamespace(get_by_email=AsyncMock(return_value=provider_user))
    providers = SimpleNamespace(
        get_by_user_id=AsyncMock(return_value=provider_profile),
        get_by_email=AsyncMock(return_value=provider_profile),
        add=AsyncMock(),
    )
    memberships = SimpleNamespace(
        has_estate_access=AsyncMock(return_value=False),
        get_for_user_and_estate=AsyncMock(return_value=None),
        add=AsyncMock(),
    )
    events = SimpleNamespace(record=AsyncMock())
    monkeypatch.setattr(
        application_module,
        "EstateRepository",
        lambda _db: SimpleNamespace(
            get_by_id=AsyncMock(
                return_value=SimpleNamespace(
                    estate_id=12,
                    name="Ridge Close Estate",
                    is_public=True,
                    is_demo=False,
                )
            )
        ),
    )
    monkeypatch.setattr(
        application_module, "ProviderInvitationRepository", lambda _db: invitation_repo
    )
    monkeypatch.setattr(application_module, "UserRepository", lambda _db: users)
    monkeypatch.setattr(
        application_module, "ServiceProviderRepository", lambda _db: providers
    )
    monkeypatch.setattr(
        application_module, "ProviderApplicationRepository", lambda _db: object()
    )
    monkeypatch.setattr(
        application_module, "EstateMembershipRepository", lambda _db: memberships
    )
    monkeypatch.setattr(
        application_module, "EstateMembershipEventRepository", lambda _db: events
    )
    auth_response = object()
    monkeypatch.setattr(
        application_module.AuthService,
        "_build_auth_response",
        staticmethod(lambda _user: auth_response),
    )
    service = ProviderApplicationService(db, sender=FakeSender())

    result = await service.accept(ProviderInvitationAcceptRequest(token="x" * 43))

    assert result is auth_response
    providers.add.assert_not_awaited()
    memberships.add.assert_awaited_once_with(
        user_id=33,
        estate_id=12,
        property_id=None,
        membership_role="service_provider",
    )
    events.record.assert_awaited_once()
    invitation_repo.mark_accepted.assert_awaited_once()
    db.commit.assert_awaited_once()
