"""Login attempt tracking and rate limiting (ported from the team's login_attempts module).

These tests exercise the VANTAGE-native implementation: every attempt is
persisted, and an account that exceeds the configured failure window is
locked out with a 429 before credentials are checked.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.exceptions import CredentialsException, RateLimitException
from app.identity.schemas.auth import LoginRequest
from app.identity.services.auth_service import AuthService
from app.main import app


def _service(*, failures: int, user: object | None = None) -> AuthService:
    service = AuthService.__new__(AuthService)
    service._settings = get_settings()
    service._db = AsyncMock()
    service._repo = AsyncMock()
    service._repo.get_by_email.return_value = user
    service._attempt_repo = AsyncMock()
    service._attempt_repo.count_recent_failures.return_value = failures
    return service


def _user() -> SimpleNamespace:
    return SimpleNamespace(
        user_id=7,
        email="resident@example.com",
        full_name="Resident Person",
        role="resident",
        unit_no="A1",
        email_verified=True,
        hoa_approved=True,
        password_hash="stored-hash",
    )


@pytest.mark.asyncio
async def test_login_blocked_after_too_many_recent_failures() -> None:
    service = _service(failures=get_settings().LOGIN_MAX_FAILED_ATTEMPTS)

    with pytest.raises(RateLimitException) as exc:
        await service.login(LoginRequest(email="user@example.com", password="Password123!"))

    assert exc.value.status_code == 429
    service._repo.get_by_email.assert_not_awaited()
    service._attempt_repo.record.assert_not_awaited()


@pytest.mark.asyncio
async def test_failed_login_records_attempt_and_commits(monkeypatch) -> None:
    service = _service(failures=0, user=_user())
    monkeypatch.setattr(
        "app.identity.services.auth_service.verify_password", lambda *a, **k: False
    )

    with pytest.raises(CredentialsException):
        await service.login(
            LoginRequest(email="resident@example.com", password="wrong-password"),
            ip_address="203.0.113.7",
        )

    service._attempt_repo.record.assert_awaited_once_with(
        email="resident@example.com", ip_address="203.0.113.7", successful=False
    )
    service._db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_successful_login_records_success(monkeypatch) -> None:
    service = _service(failures=0, user=_user())
    monkeypatch.setattr(
        "app.identity.services.auth_service.verify_password", lambda *a, **k: True
    )

    result = await service.login(
        LoginRequest(email="resident@example.com", password="correct-password"),
        ip_address="203.0.113.7",
    )

    assert result.access_token
    assert result.user.user_id == 7
    service._attempt_repo.record.assert_awaited_once_with(
        email="resident@example.com", ip_address="203.0.113.7", successful=True
    )


class _FakeSession:
    async def execute(self, *args, **kwargs):
        raise AssertionError("rate-limit path should not query the database")

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def close(self) -> None:
        pass


def test_login_rate_limit_returns_429_envelope(monkeypatch) -> None:
    async def _blocked(self, *, email, since):
        return get_settings().LOGIN_MAX_FAILED_ATTEMPTS

    monkeypatch.setattr(
        "app.identity.repositories.login_attempt_repository.LoginAttemptRepository.count_recent_failures",
        _blocked,
    )

    from app.db.session import get_db

    async def _override_get_db():
        yield _FakeSession()

    app.dependency_overrides[get_db] = _override_get_db
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "Password123!"},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "RATE_LIMITED"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_db_login_attempt_persistence_and_lockout(db_session, async_client) -> None:
    """Exercise login attempts, failure recording, and account lockout against real PostgreSQL."""
    from sqlalchemy import select, func
    from app.identity.models.login_attempt import LoginAttempts
    from app.identity.models.user import User
    from app.core.security import hash_password

    # 1. Seed a user directly in the database
    user = User(
        email="realuser@example.com",
        password_hash=hash_password("CorrectPass123!"),
        full_name="Real Valora User",
        role="resident",
        unit_no="B12",
        phoneno="0821112233",
        email_verified=True,
        hoa_approved=True,
    )
    db_session.add(user)
    await db_session.commit()

    # 2. Attempt login with wrong password multiple times
    max_failures = get_settings().LOGIN_MAX_FAILED_ATTEMPTS
    for i in range(max_failures):
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "realuser@example.com", "password": "WrongPassword!"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "UNAUTHENTICATED"

    # 3. Verify attempts were persisted in real PostgreSQL
    res = await db_session.execute(
        select(func.count())
        .select_from(LoginAttempts)
        .where(
            LoginAttempts.email == "realuser@example.com",
            LoginAttempts.successful.is_(False),
        )
    )
    failure_count = res.scalar_one()
    assert failure_count == max_failures

    # 4. Attempt login with correct password now that threshold is met -> 429 lockout
    lockout_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "realuser@example.com", "password": "CorrectPass123!"},
    )
    assert lockout_resp.status_code == 429
    assert lockout_resp.json()["detail"]["code"] == "RATE_LIMITED"

    # 5. Non-existent user also records failure attempts in real PostgreSQL
    ghost_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "AnyPassword123!"},
    )
    assert ghost_resp.status_code == 401
    assert ghost_resp.json()["detail"]["code"] == "UNAUTHENTICATED"
    ghost_attempts = await db_session.execute(
        select(func.count())
        .select_from(LoginAttempts)
        .where(
            LoginAttempts.email == "nonexistent@example.com",
            LoginAttempts.successful.is_(False),
        )
    )
    assert ghost_attempts.scalar_one() == 1
