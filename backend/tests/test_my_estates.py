"""Unit tests for GET /api/v1/auth/estates (server-resolved estate access list).

These are pure-service tests with in-memory fakes, matching the existing
``test_estate_authorization.py`` style, so they run without a database.
"""
from types import SimpleNamespace

import pytest

from app.common.enums import UserRole
from app.identity.services.estate_authorization_service import EstateAuthorizationService


def _membership(estate_id: int, role: str, property_id: int | None = None):
    return SimpleNamespace(
        membership_id=estate_id * 100 + (property_id or 0),
        estate_id=estate_id,
        membership_role=role,
        property_id=property_id,
    )


def _estate(estate_id: int, name: str, is_demo: bool = False):
    return SimpleNamespace(
        estate_id=estate_id,
        name=name,
        suburb=f"Suburb {estate_id}",
        city="Pretoria",
        province="Gauteng",
        is_demo=is_demo,
    )


class FakeMembershipRepository:
    def __init__(self, memberships):
        self._memberships = memberships

    async def list_for_user(self, *, user_id: int):
        return list(self._memberships)


class FakeEstateRepository:
    def __init__(self, estates):
        self._estates = {e.estate_id: e for e in estates}

    async def get_many_by_ids(self, estate_ids):
        return {eid: self._estates[eid] for eid in estate_ids if eid in self._estates}


def _service(memberships, estates):
    service = EstateAuthorizationService.__new__(EstateAuthorizationService)
    service._memberships = FakeMembershipRepository(memberships)
    service._estates = FakeEstateRepository(estates)
    return service


@pytest.mark.asyncio
async def test_user_without_membership_has_no_estates() -> None:
    service = _service([], [_estate(1, "Zambezi Country Estate")])
    actor = SimpleNamespace(user_id=5, role=UserRole.resident.value)

    assert await service.list_accessible_estates(actor) == []


@pytest.mark.asyncio
async def test_memberships_are_grouped_per_estate_with_unioned_properties() -> None:
    memberships = [
        _membership(2, UserRole.resident.value, property_id=20),
        _membership(1, UserRole.resident.value, property_id=10),
        _membership(1, UserRole.resident.value, property_id=11),
    ]
    estates = [_estate(1, "Zambezi Country Estate"), _estate(2, "Amberfield Estate")]
    actor = SimpleNamespace(user_id=5, role=UserRole.resident.value)

    summaries = await _service(memberships, estates).list_accessible_estates(actor)

    assert [s.estate_name for s in summaries] == ["Amberfield Estate", "Zambezi Country Estate"]
    zambezi = next(s for s in summaries if s.estate_id == 1)
    assert zambezi.property_ids == frozenset({10, 11})
    assert zambezi.membership_roles == frozenset({UserRole.resident.value})
    assert zambezi.is_estate_admin is False


@pytest.mark.asyncio
async def test_admin_flag_requires_both_global_role_and_estate_membership_role() -> None:
    memberships = [_membership(1, UserRole.hoa_admin.value)]
    estates = [_estate(1, "Zambezi Country Estate")]

    admin = SimpleNamespace(user_id=5, role=UserRole.hoa_admin.value)
    resident_global = SimpleNamespace(user_id=6, role=UserRole.resident.value)

    assert (await _service(memberships, estates).list_accessible_estates(admin))[0].is_estate_admin

    downgraded = await _service(memberships, estates).list_accessible_estates(resident_global)
    assert downgraded[0].is_estate_admin is False


@pytest.mark.asyncio
async def test_demo_estates_are_flagged_in_the_access_summary() -> None:
    memberships = [_membership(1, UserRole.resident.value)]
    estates = [
        _estate(1, "Demo Estate", is_demo=True),
        _estate(2, "Real Estate", is_demo=False),
    ]
    memberships.append(_membership(2, UserRole.resident.value))
    actor = SimpleNamespace(user_id=5, role=UserRole.resident.value)

    summaries = await _service(memberships, estates).list_accessible_estates(actor)

    by_id = {s.estate_id: s for s in summaries}
    assert by_id[1].is_demo is True
    assert by_id[2].is_demo is False


@pytest.mark.asyncio
async def test_membership_pointing_at_a_missing_estate_is_skipped() -> None:
    memberships = [_membership(999, UserRole.resident.value)]
    service = _service(memberships, [_estate(1, "Zambezi Country Estate")])
    actor = SimpleNamespace(user_id=5, role=UserRole.resident.value)

    assert await service.list_accessible_estates(actor) == []
