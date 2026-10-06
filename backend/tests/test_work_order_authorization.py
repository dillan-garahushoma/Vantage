from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.common.enums import UserRole, WorkOrderStatus
from app.community.schemas.work_order import WorkOrderRating, WorkOrderUpdate
from app.community.services.work_order_service import WorkOrderService
from app.core.exceptions import ConflictException, ForbiddenException


def _work_order() -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        work_order_id=41,
        estate_id=4,
        complaint_id=31,
        provider_id=10,
        assigned_at=now,
        resolved_at=None,
        job_cost=None,
        resident_rating=None,
        completion_notes=None,
        status=WorkOrderStatus.assigned.value,
        estimated_completion_date=None,
        actual_completion_date=None,
        created_at=now,
        updated_at=now,
    )


class FakeEstateAuthorization:
    async def require_role(self, **kwargs):
        return SimpleNamespace(membership_role=kwargs["actor"].role)


class FakeWorkOrders:
    def __init__(self, work_order):
        self.work_order = work_order

    async def get_by_id_in_estate(self, *, work_order_id: int, estate_id: int):
        if work_order_id == self.work_order.work_order_id and estate_id == self.work_order.estate_id:
            return self.work_order
        return None


class FakeProviders:
    def __init__(self, provider):
        self.provider = provider

    async def get_by_user_id(self, user_id: int):
        return self.provider


@pytest.mark.asyncio
async def test_provider_cannot_update_another_providers_work_order() -> None:
    service = WorkOrderService.__new__(WorkOrderService)
    service._repo = FakeWorkOrders(_work_order())
    service._provider_repo = FakeProviders(SimpleNamespace(provider_id=11))
    service._estate_authorization = FakeEstateAuthorization()
    provider_user = SimpleNamespace(user_id=22, role=UserRole.service_provider.value)

    with pytest.raises(ForbiddenException):
        await service.update_work_order(
            41,
            WorkOrderUpdate(status=WorkOrderStatus.in_progress),
            provider_user,
            estate_id=4,
        )


@pytest.mark.asyncio
async def test_resident_cannot_rate_a_work_order_twice() -> None:
    work_order = _work_order()
    work_order.status = WorkOrderStatus.completed.value
    work_order.resident_rating = 4
    service = WorkOrderService.__new__(WorkOrderService)
    service._repo = FakeWorkOrders(work_order)
    service._estate_authorization = FakeEstateAuthorization()
    service._complaint_repo = SimpleNamespace(
        get_by_id=lambda complaint_id: _async(SimpleNamespace(user_id=8))
    )
    resident = SimpleNamespace(user_id=8, role=UserRole.resident.value)

    with pytest.raises(ConflictException):
        await service.rate_work_order(41, WorkOrderRating(rating=5), resident, estate_id=4)


async def _async(value):
    return value
