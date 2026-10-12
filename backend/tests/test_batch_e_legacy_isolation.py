from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.router import create_api_router
from app.core.config import Settings
from app.db.session import get_db
from app.identity.api.dependencies import get_current_user
from app.providers.schemas.review import PaginatedReviewsResponse, ReviewResponse
from app.providers.schemas.service_provider import (
    ServiceProviderResponse,
)
from app.property.schemas.listing import PaginatedListingsResponse
from app.property.schemas.sale import PaginatedSalesResponse
from app.providers.services.review_service import ReviewService
from app.providers.services.service_provider_service import ServiceProviderService
from app.property.services.listing_service import ListingService
from app.property.services.sale_service import SaleService


def _client(enable_legacy_routes: bool, role: str = "hoa_admin") -> TestClient:
    app = FastAPI()
    app.include_router(create_api_router(enable_legacy_routes))
    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        user_id=7, role=role
    )
    return TestClient(app)


def test_legacy_routes_are_absent_and_return_404_by_default() -> None:
    assert Settings(
        DATABASE_URL="postgresql+asyncpg://localhost/valora_test",
        SECRET_KEY="test-secret-not-for-production",
    ).ENABLE_LEGACY_ROUTES is False

    client = _client(False)
    paths = client.get("/openapi.json").json()["paths"]
    legacy_paths = (
        "/api/v1/listings",
        "/api/v1/sales",
        "/api/v1/providers/{provider_id}/reviews",
    )
    for path in legacy_paths:
        assert path not in paths

    assert client.get("/api/v1/listings").status_code == 404
    assert client.get("/api/v1/sales").status_code == 404
    assert client.get("/api/v1/providers/1/reviews").status_code == 404
    assert client.post("/api/v1/providers").status_code == 404
    assert client.patch("/api/v1/providers/1").status_code == 404
    assert client.post("/api/v1/providers/1/reviews").status_code == 404


def test_legacy_routes_work_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    listing_response = PaginatedListingsResponse(count=0, page=1, page_size=20, listings=[])
    sales_response = PaginatedSalesResponse(count=0, page=1, page_size=20, sales=[])
    reviews_response = PaginatedReviewsResponse(count=0, reviews=[])
    provider_response = ServiceProviderResponse(
        provider_id=1,
        full_name="Provider One",
        trade="plumber",
        phone="+123456789",
        email="provider@example.com",
        avg_rating=Decimal("4.50"),
        total_reviews=1,
        verified=True,
        emergency_available=False,
    )
    review_response = ReviewResponse(
        review_id=1,
        user_id=7,
        provider_id=1,
        rating=5,
        comment="Great",
        created_at=datetime.now(timezone.utc),
    )
    monkeypatch.setattr(ListingService, "search_listings", AsyncMock(return_value=listing_response))
    monkeypatch.setattr(SaleService, "list_sales", AsyncMock(return_value=sales_response))
    monkeypatch.setattr(ReviewService, "list_reviews", AsyncMock(return_value=reviews_response))
    monkeypatch.setattr(ReviewService, "create_review", AsyncMock(return_value=review_response))
    monkeypatch.setattr(
        ServiceProviderService, "create_provider", AsyncMock(return_value=provider_response)
    )
    monkeypatch.setattr(
        ServiceProviderService, "update_provider", AsyncMock(return_value=provider_response)
    )

    # Provider create/update is a platform-operator action (ONB-1), so this
    # client carries platform_admin; the listing/sale reads ignore the role.
    client = _client(True, role="platform_admin")
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/listings" in paths
    assert "/api/v1/sales" in paths
    assert "/api/v1/providers/{provider_id}/reviews" in paths

    assert client.get("/api/v1/listings").status_code == 200
    assert client.get("/api/v1/sales").status_code == 200
    assert client.get("/api/v1/providers/1/reviews").status_code == 200
    assert client.post(
        "/api/v1/providers",
        json={
            "full_name": "Provider One",
            "trade": "plumber",
            "phone": "+123456789",
            "email": "provider@example.com",
        },
    ).status_code == 201
    assert client.patch(
        "/api/v1/providers/1", json={"verified": True}
    ).status_code == 200
    resident_client = _client(True, role="resident")
    assert resident_client.post(
        "/api/v1/providers/1/reviews", json={"rating": 5, "comment": "Great"}
    ).status_code == 201


def _provider(provider_id: int = 1, user_id: int | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        provider_id=provider_id,
        user_id=user_id,
        full_name="Provider One",
        trade="plumber",
        phone="+123456789",
        email="provider@example.test",
        avg_rating=Decimal("4.50"),
        total_reviews=1,
        verified=True,
        emergency_available=False,
    )


@pytest.mark.asyncio
async def test_provider_directory_requires_that_estate_admin_membership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ONB master P1: the directory is estate-scoped, not "any estate I admin"."""
    repo = SimpleNamespace(
        get_all_in_estate=AsyncMock(return_value=[_provider()]),
        count_in_estate=AsyncMock(return_value=1),
    )
    authorization = SimpleNamespace(require_role=AsyncMock(return_value=None))
    monkeypatch.setattr(
        "app.providers.services.service_provider_service.ServiceProviderRepository",
        lambda _db: repo,
    )
    monkeypatch.setattr(
        "app.providers.services.service_provider_service.EstateAuthorizationService",
        lambda _db: authorization,
    )
    admin = SimpleNamespace(user_id=10, role="hoa_admin")
    result = await ServiceProviderService(object()).list_providers(
        actor=admin, estate_id=5, page=1, size=20
    )
    assert result.total == 1
    assert len(result.items) == 1
    authorization.require_role.assert_awaited_once_with(
        actor=admin, estate_id=5, allowed_roles=("hoa_admin",)
    )
    repo.get_all_in_estate.assert_awaited_once()
    assert repo.get_all_in_estate.await_args.kwargs["estate_id"] == 5
    assert repo.count_in_estate.await_args.kwargs["estate_id"] == 5


@pytest.mark.asyncio
async def test_provider_reads_deny_residents_and_admins_without_membership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.exceptions import ForbiddenException

    repo = SimpleNamespace(
        get_all_in_estate=AsyncMock(return_value=[]),
        count_in_estate=AsyncMock(return_value=0),
        get_by_id_in_estate=AsyncMock(return_value=_provider()),
        get_by_user_id=AsyncMock(return_value=_provider(user_id=11)),
    )
    authorization = SimpleNamespace(
        require_role=AsyncMock(
            side_effect=ForbiddenException("You do not have access to this estate.")
        )
    )
    monkeypatch.setattr(
        "app.providers.services.service_provider_service.ServiceProviderRepository",
        lambda _db: repo,
    )
    monkeypatch.setattr(
        "app.providers.services.service_provider_service.EstateAuthorizationService",
        lambda _db: authorization,
    )
    service = ServiceProviderService(object())

    with pytest.raises(ForbiddenException):
        await service.list_providers(
            actor=SimpleNamespace(user_id=10, role="hoa_admin"), estate_id=5, page=1, size=20
        )
    with pytest.raises(ForbiddenException):
        await service.list_providers(
            actor=SimpleNamespace(user_id=12, role="resident"), estate_id=5, page=1, size=20
        )
    with pytest.raises(ForbiddenException):
        await service.get_provider(
            1, SimpleNamespace(user_id=12, role="resident"), estate_id=5
        )
    with pytest.raises(ForbiddenException):
        await service.get_provider(
            1, SimpleNamespace(user_id=10, role="hoa_admin"), estate_id=5
        )


@pytest.mark.asyncio
async def test_provider_can_read_only_own_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.exceptions import ForbiddenException

    repo = SimpleNamespace(
        get_by_user_id=AsyncMock(return_value=_provider(user_id=11)),
        get_by_id_in_estate=AsyncMock(),
    )
    authorization = SimpleNamespace(require_role=AsyncMock(return_value=None))
    monkeypatch.setattr(
        "app.providers.services.service_provider_service.ServiceProviderRepository",
        lambda _db: repo,
    )
    monkeypatch.setattr(
        "app.providers.services.service_provider_service.EstateAuthorizationService",
        lambda _db: authorization,
    )
    service = ServiceProviderService(object())
    provider_actor = SimpleNamespace(user_id=11, role="service_provider")

    result = await service.get_provider(1, provider_actor, estate_id=5)
    assert result.provider_id == 1
    repo.get_by_user_id.assert_awaited_once_with(11)
    repo.get_by_id_in_estate.assert_not_awaited()
    authorization.require_role.assert_awaited_once_with(
        actor=provider_actor, estate_id=5, allowed_roles=("service_provider",)
    )

    with pytest.raises(ForbiddenException):
        await service.get_provider(2, provider_actor, estate_id=5)
