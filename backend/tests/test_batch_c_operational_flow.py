from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.common.enums import ComplaintStatus, UserRole, WorkOrderStatus
from app.community.schemas.work_order import WorkOrderCreate, WorkOrderRating, WorkOrderUpdate
from app.community.services.work_order_service import WorkOrderService
from app.core.exceptions import ConflictException


def _make_complaint(status: str = "reviewed") -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        complaint_id=10,
        user_id=100,
        estate_id=1,
        unit_id=101,
        category="plumbing",
        description="Leaking geyser",
        priority="high",
        is_anonymous=False,
        status=status,
        assigned_to=None,
        reviewed_at=now,
        assigned_at=None,
        started_at=None,
        resolved_at=None,
        created_at=now,
        updated_at=now,
    )


def _make_work_order(status: str = "assigned") -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        work_order_id=20,
        complaint_id=10,
        estate_id=1,
        provider_id=5,
        assigned_at=now,
        resolved_at=None,
        job_cost=None,
        resident_rating=None,
        completion_notes=None,
        status=status,
        estimated_completion_date=None,
        actual_completion_date=None,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_c1_create_work_order_requires_reviewed_status() -> None:
    service = WorkOrderService.__new__(WorkOrderService)
    service._estate_authorization = SimpleNamespace(
        require_role=AsyncMock(return_value=None),
        resolve_access=AsyncMock(),
    )
    unreviewed = _make_complaint(status="submitted")
    service._complaint_repo = SimpleNamespace(
        get_by_id_in_estate=AsyncMock(return_value=unreviewed),
    )
    admin = SimpleNamespace(user_id=1, role="hoa_admin")

    with pytest.raises(ConflictException, match="reviewed"):
        await service.create_work_order(
            WorkOrderCreate(complaint_id=10, provider_id=5),
            admin,
            estate_id=1,
        )


@pytest.mark.asyncio
async def test_c1_create_work_order_rejects_duplicate_active_work_order() -> None:
    service = WorkOrderService.__new__(WorkOrderService)
    service._estate_authorization = SimpleNamespace(
        require_role=AsyncMock(return_value=None),
        resolve_access=AsyncMock(),
    )
    complaint = _make_complaint(status="reviewed")
    service._complaint_repo = SimpleNamespace(
        get_by_id_in_estate=AsyncMock(return_value=complaint),
    )
    service._repo = SimpleNamespace(
        get_active_for_complaint=AsyncMock(return_value=_make_work_order(status="in_progress")),
    )
    admin = SimpleNamespace(user_id=1, role="hoa_admin")

    with pytest.raises(ConflictException, match="active work order"):
        await service.create_work_order(
            WorkOrderCreate(complaint_id=10, provider_id=5),
            admin,
            estate_id=1,
        )


@pytest.mark.asyncio
async def test_c2_update_work_order_rejects_reopening_completed() -> None:
    service = WorkOrderService.__new__(WorkOrderService)
    service._estate_authorization = SimpleNamespace(
        require_role=AsyncMock(return_value=None),
    )
    completed_wo = _make_work_order(status="completed")
    service._repo = SimpleNamespace(
        get_by_id_in_estate=AsyncMock(return_value=completed_wo),
    )
    service._provider_repo = SimpleNamespace(
        get_by_user_id=AsyncMock(return_value=SimpleNamespace(provider_id=5)),
    )
    provider_user = SimpleNamespace(user_id=50, role="service_provider")

    with pytest.raises(ConflictException, match="completed work order cannot be re-opened"):
        await service.update_work_order(
            20,
            WorkOrderUpdate(status=WorkOrderStatus.in_progress),
            provider_user,
            estate_id=1,
        )


@pytest.mark.asyncio
async def test_c2_update_work_order_rejects_skipping_steps() -> None:
    service = WorkOrderService.__new__(WorkOrderService)
    service._estate_authorization = SimpleNamespace(
        require_role=AsyncMock(return_value=None),
    )
    assigned_wo = _make_work_order(status="assigned")
    service._repo = SimpleNamespace(
        get_by_id_in_estate=AsyncMock(return_value=assigned_wo),
    )
    service._provider_repo = SimpleNamespace(
        get_by_user_id=AsyncMock(return_value=SimpleNamespace(provider_id=5)),
    )
    provider_user = SimpleNamespace(user_id=50, role="service_provider")

    # Trying to jump from assigned directly to completed
    with pytest.raises(ConflictException, match="must be in_progress before"):
        await service.update_work_order(
            20,
            WorkOrderUpdate(status=WorkOrderStatus.completed),
            provider_user,
            estate_id=1,
        )


@pytest.mark.asyncio
async def test_c3_rate_work_order_recomputes_provider_aggregates() -> None:
    service = WorkOrderService.__new__(WorkOrderService)
    service._estate_authorization = SimpleNamespace(
        require_role=AsyncMock(return_value=None),
    )
    completed_wo = _make_work_order(status="completed")
    complaint = _make_complaint(status="resolved")

    provider = SimpleNamespace(provider_id=5, avg_rating=None, total_reviews=0)
    saved_provider = []

    service._repo = SimpleNamespace(
        get_by_id_in_estate_for_update=AsyncMock(return_value=completed_wo),
        get_provider_rating_aggregate=AsyncMock(return_value=(Decimal("4.50"), 2)),
        get_latest_for_complaint=AsyncMock(return_value=completed_wo),
        save=AsyncMock(return_value=completed_wo),
    )
    service._complaint_repo = SimpleNamespace(
        get_by_id_in_estate=AsyncMock(return_value=complaint),
        record_transition=AsyncMock(return_value=complaint),
    )
    service._provider_repo = SimpleNamespace(
        get_by_id=AsyncMock(return_value=provider),
        save=AsyncMock(side_effect=lambda p: saved_provider.append(p)),
    )
    service._db = SimpleNamespace(
        commit=AsyncMock(),
        refresh=AsyncMock(),
        rollback=AsyncMock(),
    )

    resident = SimpleNamespace(user_id=100, role="resident")
    res = await service.rate_work_order(20, WorkOrderRating(rating=5), resident, estate_id=1)

    assert res.resident_rating == 5
    assert complaint.status == "rated"
    assert provider.avg_rating == Decimal("4.50")
    assert provider.total_reviews == 2
    assert service._db.commit.called


@pytest.mark.asyncio
async def test_c5_atomicity_injected_failure_rolls_back() -> None:
    service = WorkOrderService.__new__(WorkOrderService)
    service._estate_authorization = SimpleNamespace(
        require_role=AsyncMock(return_value=None),
    )
    completed_wo = _make_work_order(status="completed")
    complaint = _make_complaint(status="resolved")

    # Injected failure on complaint transition
    service._repo = SimpleNamespace(
        get_by_id_in_estate_for_update=AsyncMock(return_value=completed_wo),
        save=AsyncMock(return_value=completed_wo),
        get_latest_for_complaint=AsyncMock(return_value=completed_wo),
    )
    service._complaint_repo = SimpleNamespace(
        get_by_id_in_estate=AsyncMock(return_value=complaint),
        record_transition=AsyncMock(side_effect=RuntimeError("DB write failure")),
    )
    service._provider_repo = SimpleNamespace()
    mock_db = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )
    service._db = mock_db

    resident = SimpleNamespace(user_id=100, role="resident")

    with pytest.raises(RuntimeError, match="DB write failure"):
        await service.rate_work_order(20, WorkOrderRating(rating=5), resident, estate_id=1)

    assert mock_db.rollback.called
    assert not mock_db.commit.called
