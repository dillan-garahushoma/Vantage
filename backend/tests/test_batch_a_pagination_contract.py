from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.common.pagination import Page, PaginationParams
from app.community.schemas.announcement import AnnouncementResponse
from app.community.schemas.complaint import ComplaintResponse
from app.community.schemas.work_order import WorkOrderResponse
from app.db.session import get_db
from app.identity.api.dependencies import get_current_user
from app.main import app
from app.property.schemas.property import PropertyResponse
from app.providers.schemas.service_provider import ServiceProviderResponse


client = TestClient(app)
now = datetime.now(timezone.utc)


def test_page_envelope_calculates_page_count() -> None:
    response = Page[int](items=[1, 2], total=22, page=2, size=10)

    assert response.model_dump() == {
        "items": [1, 2],
        "total": 22,
        "page": 2,
        "size": 10,
        "pages": 3,
    }

    empty_page = Page[int](items=[], total=22, page=4, size=10)
    assert empty_page.items == []
    assert empty_page.total == 22
    assert empty_page.pages == 3


def test_pagination_parameters_use_size_and_reject_more_than_100() -> None:
    assert PaginationParams(page=2, size=50).offset == 50

    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        user_id=1, role="hoa_admin"
    )
    try:
        assert client.get("/api/v1/complaints?estate_id=1&size=101").status_code == 422
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


def test_complaint_and_work_order_sort_values_are_allow_listed() -> None:
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        user_id=1, role="hoa_admin"
    )
    try:
        assert client.get(
            "/api/v1/complaints?estate_id=1&sort=secret_column"
        ).status_code == 422
        assert client.get(
            "/api/v1/work-orders?estate_id=1&sort=secret_column"
        ).status_code == 422
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


def test_openapi_operation_ids_are_readable_and_stable() -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert paths["/api/v1/complaints"]["get"]["operationId"] == (
        "complaints_list_complaints"
    )
    assert paths["/api/v1/work-orders"]["get"]["operationId"] == (
        "work_orders_list_work_orders"
    )


def test_all_nonlegacy_list_endpoints_return_the_standard_envelope_and_id_alias(
    monkeypatch,
) -> None:
    from app.community.services.announcement_service import AnnouncementService
    from app.community.services.complaint_service import ComplaintService
    from app.community.services.work_order_service import WorkOrderService
    from app.property.services.property_service import PropertyService
    from app.providers.services.service_provider_service import ServiceProviderService

    responses = [
        (
            "/api/v1/complaints",
            ComplaintService,
            "list_complaints",
            "complaint_id",
            ComplaintResponse(
                complaint_id=11,
                user_id=1,
                estate_id=1,
                unit_id=3,
                category="maintenance",
                description="Leaking shared pipe.",
                priority="normal",
                is_anonymous=False,
                status="submitted",
                assigned_to=None,
                reviewed_at=None,
                assigned_at=None,
                started_at=None,
                resolved_at=None,
                created_at=now,
                updated_at=now,
            ),
        ),
        (
            "/api/v1/work-orders",
            WorkOrderService,
            "list_work_orders",
            "work_order_id",
            WorkOrderResponse(
                work_order_id=12,
                complaint_id=11,
                provider_id=4,
                assigned_at=now,
                resolved_at=None,
                job_cost=Decimal("10.00"),
                resident_rating=None,
                completion_notes=None,
                status="assigned",
                estimated_completion_date=None,
                actual_completion_date=None,
                created_at=now,
                updated_at=now,
            ),
        ),
        (
            "/api/v1/announcements",
            AnnouncementService,
            "list_announcements",
            "announcement_id",
            AnnouncementResponse(
                announcement_id=13,
                estate_id=1,
                title="Water shutdown",
                message="Water will be off tomorrow.",
                created_by=1,
                expires_at=None,
                created_at=now,
                updated_at=now,
            ),
        ),
        (
            "/api/v1/properties",
            PropertyService,
            "search_properties",
            "unit_id",
            PropertyResponse(
                unit_id=14,
                estate_id=1,
                unit_no="A-101",
                complex_name="Estate",
                street_address="1 Road",
                suburb=None,
                size_m2=Decimal("100.00"),
                bedrooms=2,
                bathrooms=1,
            ),
        ),
        (
            "/api/v1/providers",
            ServiceProviderService,
            "list_providers",
            "provider_id",
            ServiceProviderResponse(
                provider_id=15,
                full_name="Provider",
                trade="plumbing",
                phone="0123456789",
                email="provider@example.test",
                avg_rating=Decimal("4.50"),
                total_reviews=2,
                verified=True,
                emergency_available=False,
            ),
        ),
    ]
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        user_id=1, role="hoa_admin"
    )
    try:
        for path, service, method, identifier_field, item in responses:
            page = Page[type(item)](items=[item], total=21, page=3, size=10)
            monkeypatch.setattr(service, method, AsyncMock(return_value=page))
            response = client.get(f"{path}?estate_id=1&page=3&size=10")

            assert response.status_code == 200, response.text
            body = response.json()
            assert set(body) == {"items", "total", "page", "size", "pages"}
            assert body["total"] == 21
            assert body["page"] == 3
            assert body["size"] == 10
            assert body["pages"] == 3
            assert "id" in body["items"][0]
            assert identifier_field not in body["items"][0]
            assert client.get(f"{path}?estate_id=1&size=101").status_code == 422

        monkeypatch.setattr(
            ComplaintService,
            "list_complaints",
            AsyncMock(return_value=Page[ComplaintResponse](
                items=[], total=21, page=4, size=10
            )),
        )
        beyond_end = client.get(
            "/api/v1/complaints?estate_id=1&page=4&size=10"
        )
        assert beyond_end.status_code == 200, beyond_end.text
        assert beyond_end.json() == {
            "items": [],
            "total": 21,
            "page": 4,
            "size": 10,
            "pages": 3,
        }
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)
