"""HTTP mapping for AIUnavailableError (BATCH AI-2).

The AI layer must degrade to a clean 503 that never leaks a key, a prompt or a
provider response.
"""

from __future__ import annotations

import httpx
import pytest

from app.core.ai.errors import AIUnavailableError
from app.main import app

TEST_PATH = "/_test/ai-unavailable"


@pytest.mark.asyncio
async def test_ai_unavailable_maps_to_a_503_envelope() -> None:
    async def _raise_budget() -> None:
        raise AIUnavailableError("budget")

    app.add_api_route(TEST_PATH, _raise_budget, methods=["GET"])
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                TEST_PATH, headers={"X-Request-ID": "req-ai-503"}
            )
    finally:
        app.router.routes = [
            route
            for route in app.router.routes
            if getattr(route, "path", None) != TEST_PATH
        ]

    assert response.status_code == 503
    assert response.headers["X-Request-ID"] == "req-ai-503"

    error = response.json()["detail"]
    assert error["code"] == "AI_UNAVAILABLE"
    assert error["request_id"] == "req-ai-503"
    assert error["details"] == {"reason": "budget"}
    assert isinstance(error["message"], str) and error["message"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reason",
    [
        "disabled",
        "policy",
        "budget",
        "timeout",
        "network",
        "provider_error",
        "rate_limited",
        "invalid_output",
        "truncated",
    ],
)
async def test_every_reason_maps_to_503_with_a_safe_body(reason: str) -> None:
    async def _raise() -> None:
        raise AIUnavailableError(reason)

    app.add_api_route(TEST_PATH, _raise, methods=["GET"])
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(TEST_PATH)
    finally:
        app.router.routes = [
            route
            for route in app.router.routes
            if getattr(route, "path", None) != TEST_PATH
        ]

    assert response.status_code == 503
    body = response.json()["detail"]
    assert body["code"] == "AI_UNAVAILABLE"
    assert body["details"] == {"reason": reason}
    # The reason code is the only AI detail that leaves the process.
    assert "key" not in str(body).lower()
    assert "prompt" not in str(body).lower()


def test_handler_is_registered_on_the_application() -> None:
    assert AIUnavailableError in app.exception_handlers
