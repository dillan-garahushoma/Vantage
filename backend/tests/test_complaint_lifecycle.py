from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.common.enums import ComplaintStatus, UserRole
from app.community.schemas.complaint import ComplaintStatusUpdate
from app.community.services.complaint_service import ComplaintService
from app.core.exceptions import ForbiddenException, NotFoundException


def _complaint(status: str = "submitted") -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        complaint_id=31,
        user_id=8,
        estate_id=2,
        unit_id=19,
        category="water",
        description="Water leak at the shared inlet.",
        priority="normal",
        is_anonymous=False,
        status=status,
        assigned_to=None,
        reviewed_at=None,
        assigned_at=None,
        started_at=None,
        resolved_at=None,
        created_at=now,
        updated_at=now,
    )


class FakeComplaintRepository:
    def __init__(self, complaint):
        self.complaint = complaint
        self.transitions: list[dict[str, object]] = []

    async def get_by_id_in_estate(self, *, complaint_id: int, estate_id: int):
        if complaint_id == self.complaint.complaint_id and estate_id == self.complaint.estate_id:
            return self.complaint
        return None

    async def record_transition(self, **fields):
        self.transitions.append(fields)
        return fields["complaint"]


class FakeEstateAuthorization:
    async def require_role(self, **kwargs):
        return SimpleNamespace(membership_role=UserRole.hoa_admin.value)


@pytest.mark.asyncio
async def test_lifecycle_allows_only_the_next_transition_and_records_evidence() -> None:
    complaint = _complaint()
    repository = FakeComplaintRepository(complaint)
    service = ComplaintService.__new__(ComplaintService)
    service._repo = repository
    service._estate_authorization = FakeEstateAuthorization()
    admin = SimpleNamespace(user_id=1, role=UserRole.hoa_admin.value)

    response = await service.update_status(
        31,
        ComplaintStatusUpdate(status=ComplaintStatus.reviewed, note="Initial triage complete."),
        admin,
        estate_id=2,
    )

    assert response.status == ComplaintStatus.reviewed.value
    assert complaint.reviewed_at is not None
    assert repository.transitions == [
        {
            "complaint": complaint,
            "actor_user_id": 1,
            "from_status": ComplaintStatus.submitted.value,
            "to_status": ComplaintStatus.reviewed.value,
            "note": "Initial triage complete.",
        }
    ]


@pytest.mark.asyncio
async def test_lifecycle_rejects_skipping_review_or_assigning_without_assignee() -> None:
    complaint = _complaint()
    service = ComplaintService.__new__(ComplaintService)
    service._repo = FakeComplaintRepository(complaint)
    service._estate_authorization = FakeEstateAuthorization()
    admin = SimpleNamespace(user_id=1, role=UserRole.hoa_admin.value)

    with pytest.raises(ForbiddenException):
        await service.update_status(
            31,
            ComplaintStatusUpdate(status=ComplaintStatus.in_progress),
            admin,
            estate_id=2,
        )

    complaint.status = ComplaintStatus.reviewed.value
    with pytest.raises(ForbiddenException):
        await service.update_status(
            31,
            ComplaintStatusUpdate(status=ComplaintStatus.assigned),
            admin,
            estate_id=2,
        )


@pytest.mark.asyncio
async def test_cross_estate_complaint_lookup_is_not_exposed() -> None:
    service = ComplaintService.__new__(ComplaintService)
    service._repo = FakeComplaintRepository(_complaint())

    with pytest.raises(NotFoundException):
        await service._get_or_404_in_estate(complaint_id=31, estate_id=3)
