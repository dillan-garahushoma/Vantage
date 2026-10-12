import os
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from jose import jwt
from pydantic import ValidationError

from app.core.config import Settings
from app.core.security import create_access_token, hash_password
from app.identity.api.dependencies import get_current_user
from app.identity.schemas.auth import RegisterRequest
from app.identity.services.auth_service import AuthService
from app.main import app


client = TestClient(app)


class FakeSession:
    async def execute(self, *args, **kwargs):
        class FakeResult:
            def scalar_one_or_none(self):
                return None

            def scalars(self):
                class FakeScalars:
                    def all(self):
                        return []

                    def first(self):
                        return None

                return FakeScalars()

        return FakeResult()

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def close(self):
        pass


async def _override_get_db():
    yield FakeSession()


@pytest.fixture(autouse=True)
def override_db_dependency():
    from app.db.session import get_db

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


def test_a1_malformed_sub_returns_401_not_500() -> None:
    # A token with non-numeric sub "abc"
    token = create_access_token({"sub": "abc", "role": "resident"})
    response = client.get("/api/v1/complaints?estate_id=1", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHENTICATED"


def test_a1_missing_exp_returns_401() -> None:
    # Token without exp claim
    token = jwt.encode({"sub": "123", "role": "resident"}, "test-secret-not-for-production", algorithm="HS256")
    response = client.get("/api/v1/complaints?estate_id=1", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHENTICATED"


def test_a1_expired_token_returns_401() -> None:
    token = create_access_token({"sub": "123", "role": "resident"}, expires_delta=timedelta(seconds=-10))
    response = client.get("/api/v1/complaints?estate_id=1", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHENTICATED"


def test_a1_wrong_signature_returns_401() -> None:
    token = jwt.encode({"sub": "123", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, "wrong-secret", algorithm="HS256")
    response = client.get("/api/v1/complaints?estate_id=1", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHENTICATED"


def test_a1_deleted_user_returns_401() -> None:
    token = create_access_token({"sub": "999999", "role": "resident"})
    response = client.get("/api/v1/complaints?estate_id=1", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHENTICATED"


def test_a2_validation_error_strips_input_and_password() -> None:
    secret_pw = "pass1"  # Too short
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Test User", "email": "test@example.com", "password": secret_pw},
    )
    assert response.status_code == 422
    data = response.json()
    err_details = data["detail"]["details"]
    assert isinstance(err_details, list)
    for err in err_details:
        assert "input" not in err
        assert "ctx" not in err
        assert set(err.keys()) == {"loc", "msg", "type"}
    assert secret_pw not in response.text


def test_a3_request_id_sanitization_and_presence_on_500() -> None:
    # 1. Valid request ID preserved
    res1 = client.get("/api/v1/not-found", headers={"X-Request-ID": "valid-req-123.id_test"})
    assert res1.headers.get("X-Request-ID") == "valid-req-123.id_test"

    # 2. Overlong request ID replaced by generated UUID
    overlong = "a" * 65
    res2 = client.get("/api/v1/not-found", headers={"X-Request-ID": overlong})
    assert res2.headers.get("X-Request-ID") != overlong
    assert len(res2.headers.get("X-Request-ID")) > 0

    # 3. Illegal characters replaced
    illegal = "invalid\nid\r\n"
    res3 = client.get("/api/v1/not-found", headers={"X-Request-ID": illegal})
    assert res3.headers.get("X-Request-ID") != illegal

    # 4. 422 includes X-Request-ID
    res4 = client.post("/api/v1/auth/register", json={})
    assert "X-Request-ID" in res4.headers

    # 5. Forced 500 includes X-Request-ID
    @app.get("/api/v1/test-force-500")
    def force_500():
        raise RuntimeError("Forced internal error")

    no_raise_client = TestClient(app, raise_server_exceptions=False)
    res5 = no_raise_client.get("/api/v1/test-force-500", headers={"X-Request-ID": "test-500-req"})
    assert res5.status_code == 500
    assert res5.headers.get("X-Request-ID") == "test-500-req"
    assert res5.json()["detail"]["code"] == "INTERNAL_ERROR"
    assert res5.json()["detail"]["request_id"] == "test-500-req"


def test_a2_value_error_validator_returns_422_not_500() -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "a" * 80,  # triggers ValueError in validator
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"
    assert "Password must not exceed 72 bytes" in response.text


def test_a4_login_nonexistent_user_runs_dummy_bcrypt() -> None:
    from app.identity.schemas.auth import LoginRequest
    from app.core.exceptions import CredentialsException
    from app.identity.services.auth_service import DUMMY_PASSWORD_HASH
    import asyncio

    from app.core.config import get_settings

    with patch("app.identity.services.auth_service.verify_password", return_value=False) as mock_verify:
        service = AuthService.__new__(AuthService)
        service._settings = get_settings()
        service._db = AsyncMock()
        service._repo = AsyncMock()
        service._repo.get_by_email.return_value = None
        service._attempt_repo = AsyncMock()
        service._attempt_repo.count_recent_failures.return_value = 0
        with pytest.raises(CredentialsException):
            asyncio.run(service.login(LoginRequest(email="nonexistent@example.com", password="Password123!")))
        assert mock_verify.called
        assert mock_verify.call_args[0][1] == DUMMY_PASSWORD_HASH


def test_a4_password_max_bytes_72() -> None:
    long_pw = "a" * 73
    with pytest.raises(ValidationError) as exc:
        RegisterRequest(
            full_name="Valid Name",
            email="test@example.com",
            password=long_pw,
        )
    assert "Password must not exceed 72 bytes" in str(exc.value)


def test_a5_secret_key_validation_in_production() -> None:
    # In development, placeholder is permitted
    s_dev = Settings(ENVIRONMENT="development", DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/valora_test", SECRET_KEY="short")
    assert s_dev.ENVIRONMENT == "development"

    # In production/staging, short key must raise
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(ENVIRONMENT="production", DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/valora_test", SECRET_KEY="short")

    # In production, placeholder key must raise
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/valora_test",
            SECRET_KEY="replace-with-a-long-random-development-secret",
        )

    # In production, valid >=32 key succeeds
    s_prod = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/valora_test",
        SECRET_KEY="a" * 32,
    )
    assert s_prod.ENVIRONMENT == "production"
