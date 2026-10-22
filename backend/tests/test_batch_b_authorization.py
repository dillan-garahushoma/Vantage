from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest

from app.common.enums import ComplaintStatus, UserRole
from app.community.models.complaint import Complaint
from app.community.schemas.complaint import ComplaintCreate, ComplaintStatusUpdate
from app.community.services.complaint_service import ComplaintService
from app.community.services.announcement_service import AnnouncementService
from app.community.services.work_order_service import WorkOrderService
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.identity.models.estate_membership import EstateMembership
from app.identity.repositories.estate_membership_repository import EstateMembershipRepository
from app.identity.services.estate_authorization_service import (
    EstateAccess,
    EstateAuthorizationService,
)


class FakeMembershipRepo:
    def __init__(self, memberships: list[EstateMembership]):
        self.memberships = memberships

    async def list_for_user_and_estate(self, *, user_id: int, estate_id: int):
        return [m for m in self.memberships if m.user_id == user_id and m.estate_id == estate_id]

    async def get_for_user_and_estate(self, *, user_id: int, estate_id: int):
        matches = [m for m in self.memberships if m.user_id == user_id and m.estate_id == estate_id]
        return matches[0] if matches else None


@pytest.mark.asyncio
async def test_b1_user_with_multiple_memberships_resolves_access_without_error() -> None:
    # A user with two memberships in estate 1: one for property 101, one for property 102
    m1 = SimpleNamespace(user_id=5, estate_id=1, property_id=101, membership_role="resident")
    m2 = SimpleNamespace(user_id=5, estate_id=1, property_id=102, membership_role="resident")
    repo = FakeMembershipRepo([m1, m2])

    service = EstateAuthorizationService.__new__(EstateAuthorizationService)
    service._memberships = repo

    actor = SimpleNamespace(user_id=5, role="resident")
    access = await service.resolve_access(actor, estate_id=1)

    assert isinstance(access, EstateAccess)
    assert access.user_id == 5
    assert access.estate_id == 1
    assert access.property_ids == frozenset({101, 102})
    assert access.membership_roles == frozenset({"resident"})
    assert not access.is_estate_admin
    assert not access.is_estate_provider


@pytest.mark.asyncio
async def test_b1_dual_role_rule_hoa_admin_in_a_is_not_admin_in_b() -> None:
    # User is global hoa_admin, but in Estate 2 their membership is resident
    m_estate2 = SimpleNamespace(user_id=7, estate_id=2, property_id=201, membership_role="resident")
    repo = FakeMembershipRepo([m_estate2])

    service = EstateAuthorizationService.__new__(EstateAuthorizationService)
    service._memberships = repo

    actor = SimpleNamespace(user_id=7, role="hoa_admin")
    access = await service.resolve_access(actor, estate_id=2)

    # Must NOT be estate admin in estate 2
    assert not access.is_estate_admin

    # require_role for hoa_admin in estate 2 must raise ForbiddenException
    with pytest.raises(ForbiddenException):
        await service.require_role(actor=actor, estate_id=2, allowed_roles=("hoa_admin",))


@pytest.mark.asyncio
async def test_b3_resident_with_multiple_properties_can_report_for_both_not_third() -> None:
    m1 = SimpleNamespace(user_id=5, estate_id=1, property_id=101, membership_role="resident")
    m2 = SimpleNamespace(user_id=5, estate_id=1, property_id=102, membership_role="resident")
    repo = FakeMembershipRepo([m1, m2])

    auth_service = EstateAuthorizationService.__new__(EstateAuthorizationService)
    auth_service._memberships = repo

    class FakePropertyRepo:
        async def get_by_id_in_estate(self, *, unit_id: int, estate_id: int):
            if unit_id in {101, 102, 103} and estate_id == 1:
                return SimpleNamespace(unit_id=unit_id, estate_id=estate_id)
            return None

    class FakeComplaintRepo:
        async def create(self, **kwargs):
            return SimpleNamespace(
                complaint_id=1,
                created_at=None,
                updated_at=None,
                reviewed_at=None,
                assigned_at=None,
                started_at=None,
                resolved_at=None,
                assigned_to=None,
                status="submitted",
                **kwargs
            )

    service = ComplaintService.__new__(ComplaintService)
    service._estate_authorization = auth_service
    service._property_repo = FakePropertyRepo()
    service._repo = FakeComplaintRepo()
    service._notifications = SimpleNamespace(notify_admins=AsyncMock())
    service._db = SimpleNamespace(commit=AsyncMock())

    resident = SimpleNamespace(user_id=5, role="resident")

    # Allowed for property 101
    c1 = await service.create_complaint(
        ComplaintCreate(unit_id=101, category="noise", description="Loud music at night"),
        resident,
        estate_id=1,
    )
    assert c1.unit_id == 101

    # Allowed for property 102
    c2 = await service.create_complaint(
        ComplaintCreate(unit_id=102, category="water", description="Leaking pipe in garden"),
        resident,
        estate_id=1,
    )
    assert c2.unit_id == 102

    # Forbidden for property 103 (resident does not own 103)
    with pytest.raises(ForbiddenException):
        await service.create_complaint(
            ComplaintCreate(unit_id=103, category="parking", description="Unauthorized car"),
            resident,
            estate_id=1,
        )


@pytest.mark.asyncio
async def test_b5_anonymous_complaints_hide_author_on_events_for_hoa_viewer() -> None:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    complaint = SimpleNamespace(
        complaint_id=42,
        user_id=10,  # author
        estate_id=1,
        unit_id=101,
        category="noise",
        description="Loud disturbance",
        priority="normal",
        is_anonymous=True,
        status="submitted",
        assigned_to=None,
        reviewed_at=None,
        assigned_at=None,
        started_at=None,
        resolved_at=None,
        created_at=now,
        updated_at=now,
    )

    events = [
        SimpleNamespace(
            event_id=1,
            complaint_id=42,
            actor_user_id=10,  # author submitted event
            event_type="submitted",
            from_status=None,
            to_status="submitted",
            note=None,
            occurred_at=now,
        ),
        SimpleNamespace(
            event_id=2,
            complaint_id=42,
            actor_user_id=1,  # HOA admin reviewed event
            event_type="reviewed",
            from_status="submitted",
            to_status="reviewed",
            note="Under review",
            occurred_at=now,
        ),
    ]

    class FakeComplaintRepo:
        async def get_by_id_in_estate(self, *, complaint_id: int, estate_id: int):
            return complaint

        async def list_events(self, *, complaint_id: int):
            return events

    m_admin = SimpleNamespace(user_id=1, estate_id=1, property_id=None, membership_role="hoa_admin")
    m_author = SimpleNamespace(user_id=10, estate_id=1, property_id=101, membership_role="resident")
    repo = FakeMembershipRepo([m_admin, m_author])

    auth_service = EstateAuthorizationService.__new__(EstateAuthorizationService)
    auth_service._memberships = repo

    service = ComplaintService.__new__(ComplaintService)
    service._repo = FakeComplaintRepo()
    service._estate_authorization = auth_service

    hoa_viewer = SimpleNamespace(user_id=1, role="hoa_admin")
    author_viewer = SimpleNamespace(user_id=10, role="resident")

    # HOA viewer should see None for author's event actor_user_id on anonymous complaint
    hoa_events = await service.list_events(42, hoa_viewer, estate_id=1)
    assert hoa_events[0].actor_user_id is None
    assert hoa_events[1].actor_user_id == 1  # HOA's own action is visible

    # Author viewer sees their own user_id
    author_events = await service.list_events(42, author_viewer, estate_id=1)
    assert author_events[0].actor_user_id == 10


@pytest.mark.asyncio
async def test_b6_invalid_lifecycle_transition_raises_conflict_409() -> None:
    complaint = SimpleNamespace(
        complaint_id=31,
        user_id=8,
        estate_id=2,
        unit_id=19,
        category="water",
        description="Water leak",
        priority="normal",
        is_anonymous=False,
        status="submitted",
        assigned_to=None,
        reviewed_at=None,
        assigned_at=None,
        started_at=None,
        resolved_at=None,
        created_at=None,
        updated_at=None,
    )

    class FakeComplaintRepo:
        async def get_by_id_in_estate(self, *, complaint_id: int, estate_id: int):
            return complaint

    m_admin = SimpleNamespace(user_id=1, estate_id=2, property_id=None, membership_role="hoa_admin")
    repo = FakeMembershipRepo([m_admin])
    auth_service = EstateAuthorizationService.__new__(EstateAuthorizationService)
    auth_service._memberships = repo

    service = ComplaintService.__new__(ComplaintService)
    service._repo = FakeComplaintRepo()
    service._estate_authorization = auth_service
    admin = SimpleNamespace(user_id=1, role="hoa_admin")

    # Skipping from submitted directly to in_progress must raise ConflictException (409)
    with pytest.raises(ConflictException):
        await service.update_status(
            31,
            ComplaintStatusUpdate(status=ComplaintStatus.in_progress),
            admin,
            estate_id=2,
        )
