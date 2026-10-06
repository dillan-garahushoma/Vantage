from types import SimpleNamespace

import pytest

from app.common.enums import UserRole
from app.core.exceptions import ForbiddenException
from app.identity.schemas.auth import RegisterRequest
from app.identity.services.auth_service import AuthService
from app.identity.services.estate_authorization_service import EstateAuthorizationService


class FakeMembershipRepository:
    def __init__(self, membership):
        self.membership = membership

    async def get_for_user_and_estate(self, *, user_id: int, estate_id: int):
        return self.membership


@pytest.mark.asyncio
async def test_cross_estate_access_is_forbidden() -> None:
    service = EstateAuthorizationService.__new__(EstateAuthorizationService)
    service._memberships = FakeMembershipRepository(None)

    with pytest.raises(ForbiddenException):
        await service.require_membership(user_id=7, estate_id=99)


@pytest.mark.asyncio
async def test_privileged_action_requires_matching_estate_membership_role() -> None:
    service = EstateAuthorizationService.__new__(EstateAuthorizationService)
    actor = SimpleNamespace(user_id=7, role=UserRole.hoa_admin.value)
    service._memberships = FakeMembershipRepository(
        SimpleNamespace(membership_role=UserRole.resident.value)
    )

    with pytest.raises(ForbiddenException):
        await service.require_role(
            actor=actor, estate_id=1, allowed_roles=(UserRole.hoa_admin.value,)
        )


def test_public_registration_rejects_role_escalation_input() -> None:
    with pytest.raises(ValueError):
        RegisterRequest.model_validate(
            {
                "full_name": "Nandi Dlamini",
                "email": "nandi@example.com",
                "password": "correct-horse-battery-staple",
                "role": UserRole.hoa_admin.value,
            }
        )


@pytest.mark.asyncio
async def test_public_registration_always_creates_a_resident() -> None:
    created: dict[str, object] = {}

    class FakeUserRepository:
        async def get_by_email(self, email: str):
            return None

        async def create(self, **fields: object):
            created.update(fields)
            return SimpleNamespace(
                user_id=11,
                email=fields["email"],
                full_name=fields["full_name"],
                role=fields["role"],
                unit_no=fields["unit_no"],
                email_verified=False,
                hoa_approved=False,
            )

    service = AuthService.__new__(AuthService)
    service._repo = FakeUserRepository()
    await service.register(
        RegisterRequest(
            full_name="Nandi Dlamini",
            email="nandi@example.com",
            password="correct-horse-battery-staple",
        )
    )

    assert created["role"] == UserRole.resident.value
