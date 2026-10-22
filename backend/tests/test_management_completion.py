"""Management scope regression tests, written before implementation."""
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.router import create_api_router
from app.core.exceptions import ForbiddenException
from app.identity.schemas.auth import RegisterRequest
from app.identity.services.estate_authorization_service import EstateAuthorizationService


@pytest.mark.parametrize('legacy', [False, True])
def test_marketplace_cannot_be_reactivated(legacy):
    app = FastAPI()
    app.include_router(create_api_router(legacy))
    paths = app.openapi()['paths']
    for prefix in ('/api/v1/investment-scenarios', '/api/v1/property-market',
                   '/api/v1/listings', '/api/v1/sales'):
        assert not any(path.startswith(prefix) for path in paths)
        assert TestClient(app).get(prefix).status_code == 404
    assert '/api/v1/properties' in paths
    assert '/api/v1/residency-requests' in paths
    assert '/api/v1/analytics/intelligence/history' in paths


@pytest.mark.parametrize('account_type,extra', [
    ('estate_admin', {'estate': {'name': 'Musgrave Court', 'suburb': 'Musgrave',
                               'city': 'Durban', 'province': 'KwaZulu-Natal'}}),
    ('service_provider', {'provider': {'trade': 'plumbing', 'phone': '0821110001'}}),
])
def test_public_registration_creates_residents_only(account_type, extra):
    with pytest.raises(ValidationError):
        RegisterRequest(full_name='Test Resident', email='resident@example.com',
                        password='fictional-test-password', account_type=account_type, **extra)


@pytest.mark.asyncio
async def test_obsolete_membership_does_not_grant_estate_access():
    service = EstateAuthorizationService(object())
    service._memberships = NS(list_for_user_and_estate=AsyncMock(return_value=[
        NS(membership_role='investor', property_id=None)]))
    with pytest.raises(ForbiddenException):
        await service.resolve_access(NS(user_id=5, role='investor'), 1)


@pytest.mark.asyncio
async def test_rating_old_repair_cannot_close_a_reopened_complaint():
    from app.community.services.work_order_service import WorkOrderService
    from app.community.schemas.work_order import WorkOrderRating
    from app.core.exceptions import ConflictException
    service = WorkOrderService.__new__(WorkOrderService)
    service._db = NS(rollback=AsyncMock())
    service._estate_authorization = NS(require_role=AsyncMock())
    service._repo = NS(get_by_id_in_estate_for_update=AsyncMock(return_value=NS(
        complaint_id=1, status='completed', resident_rating=None)))
    service._complaint_repo = NS(get_by_id_in_estate=AsyncMock(return_value=NS(user_id=5, status='assigned')))
    with pytest.raises(ConflictException):
        await service.rate_work_order(1, WorkOrderRating(rating=5), NS(user_id=5), estate_id=1)


@pytest.mark.asyncio
async def test_only_latest_repair_can_rate_the_current_resolution():
    from app.community.services.work_order_service import WorkOrderService
    from app.community.schemas.work_order import WorkOrderRating
    from app.core.exceptions import ConflictException
    from tests.test_work_order_authorization import _work_order
    work = _work_order()
    work.status = 'completed'
    service = WorkOrderService.__new__(WorkOrderService)
    service._db = NS(commit=AsyncMock(), rollback=AsyncMock(), refresh=AsyncMock())
    service._estate_authorization = NS(require_role=AsyncMock())
    service._repo = NS(get_by_id_in_estate_for_update=AsyncMock(return_value=work),
        get_latest_for_complaint=AsyncMock(return_value=NS(work_order_id=42)), save=AsyncMock())
    service._complaint_repo = NS(get_by_id_in_estate=AsyncMock(return_value=NS(user_id=8, status='resolved')),
        record_transition=AsyncMock())
    with pytest.raises(ConflictException):
        await service.rate_work_order(41, WorkOrderRating(rating=5), NS(user_id=8), estate_id=4)
