"""ONB MASTER P1 — the onboarding journey, end to end, over the HTTP API.

Two kinds of test live here:

* **Policy / CLI tests** (the DTO, the operator CLI, the limiter's wording) run
  everywhere, with no database.
* **Integration tests** (``@pytest.mark.integration``) carry the claims that need
  persisted rows: the whole critical flow in one estate, the cross-estate denial
  at every step of that flow, the estate-scoped provider directory,
  ``/providers/me``, ``/work-orders/mine`` and the complaint's work order. They
  auto-skip when ``TEST_DATABASE_URL`` is unset.

The estate is the tenant boundary, so the journey test is written as a person
would walk it: an admin registers their estate, adds units, shares a code, a
resident joins and complains, the admin reviews and assigns, a provider does the
work, the resident rates it, and the score is recalculated from what actually
happened.
"""
from __future__ import annotations

import sys
import re
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from tests.operator_fixtures import signup_fixture
from pydantic import ValidationError

from app.core.exceptions import RateLimitException
from app.core.security import verify_password
from app.identity.schemas.provider_invitation import ProviderApplicationCreateRequest
from app.identity.services import provider_application_service
from app.identity.services.join_attempt_limiter import JoinAttemptLimiter, join_attempt_limiter

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import reset_password as rp  # noqa: E402

BASE = "/api/v1"
PASSWORD = "correct-horse-battery-9"

ADMIN_EMAIL = "p1_admin@example.com"
RESIDENT_EMAIL = "p1_resident@example.com"
PROVIDER_EMAIL = "p1_provider@example.com"
ESTATE_NAME = "P1 Journey Estate"

OTHER_ADMIN_EMAIL = "p1_other_admin@example.com"
OTHER_RESIDENT_EMAIL = "p1_other_resident@example.com"
OTHER_PROVIDER_EMAIL = "p1_other_provider@example.com"
OTHER_ESTATE_NAME = "P1 Other Estate"


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------- #
# Helpers that walk the public API
# --------------------------------------------------------------------------- #


async def _signup_estate_admin(client, *, name: str, email: str):
    registration = await signup_fixture(client,
        f"{BASE}/auth/register",
        json={
            "full_name": "Estate Admin",
            "email": email,
            "password": PASSWORD,
            "account_type": "estate_admin",
            "estate": {
                "name": name,
                "suburb": "Centurion",
                "city": "Pretoria",
                "province": "Gauteng",
            },
        },
    )
    assert registration.status_code == 201, registration.text
    headers = _bearer(registration.json()["access_token"])
    estates = await client.get(f"{BASE}/auth/estates", headers=headers)
    assert estates.status_code == 200, estates.text
    return headers, estates.json()["estates"][0]["estate_id"]


async def _add_units(client, headers, estate_id: int, unit_nos) -> list[int]:
    response = await client.post(
        f"{BASE}/properties/bulk?estate_id={estate_id}",
        json={
            "units": [
                {"unit_no": unit_no, "street_address": f"{unit_no} Ridge Close", "bedrooms": 3}
                for unit_no in unit_nos
            ]
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return [item["id"] for item in response.json()]


async def _issue_join_code(client, headers, estate_id: int) -> str:
    response = await client.post(
        f"{BASE}/join-codes?estate_id={estate_id}", json={}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()["code"]


async def _signup_resident(client, *, email: str) -> dict:
    response = await signup_fixture(client,
        f"{BASE}/auth/register",
        json={"full_name": "Resident One", "email": email, "password": PASSWORD},
    )
    assert response.status_code == 201, response.text
    return _bearer(response.json()["access_token"])


class _CapturingEmailSender:
    def __init__(self) -> None:
        self.messages = []

    async def send(self, message) -> None:
        self.messages.append(message)


@pytest.fixture
def provider_mailer(monkeypatch):
    sender = _CapturingEmailSender()
    monkeypatch.setattr(
        provider_application_service,
        "build_email_sender",
        lambda _settings: sender,
    )
    return sender


async def _publish_estate(db_session, estate_id: int) -> None:
    from sqlalchemy import update
    from app.property.models.estate import Estate

    await db_session.execute(
        update(Estate)
        .where(Estate.estate_id == estate_id)
        .values(is_public=True)
    )
    await db_session.commit()


async def _submit_provider_application(
    client, *, admin: dict, estate_id: int, email: str, trade: str
) -> dict:
    response = await signup_fixture(client,
        f"{BASE}/provider-applications",
        json={
            "estate_id": estate_id,
            "full_name": "Provider One",
            "email": email,
            "trade": trade,
            "phone": "082 123 4567",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _approve_provider_application(
    client,
    *,
    admin: dict,
    estate_id: int,
    application: dict,
    email: str,
    mailer: _CapturingEmailSender,
    existing_account: bool = False,
) -> dict:
    message_index = len(mailer.messages)
    approved = await client.post(
        f"{BASE}/provider-applications/{application['application_id']}/approve"
        f"?estate_id={estate_id}",
        headers=admin,
    )
    assert approved.status_code == 200, approved.text
    message = mailer.messages[message_index]
    token_match = re.search(r"#token=([A-Za-z0-9_-]+)", message.body)
    assert token_match is not None
    payload = {"token": token_match.group(1)}
    if not existing_account:
        payload["password"] = PASSWORD
    accepted = await client.post(
        f"{BASE}/auth/provider-invitations/accept",
        json=payload,
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["user"]["email"] == email
    return _bearer(accepted.json()["access_token"])


async def _apply_provider(
    db_session,
    client,
    *,
    admin: dict,
    estate_id: int,
    email: str,
    trade: str,
    mailer: _CapturingEmailSender,
    existing_account: bool = False,
) -> dict:
    await _publish_estate(db_session, estate_id)
    application = await _submit_provider_application(
        client,
        admin=admin,
        estate_id=estate_id,
        email=email,
        trade=trade,
    )
    return await _approve_provider_application(
        client,
        admin=admin,
        estate_id=estate_id,
        application=application,
        email=email,
        mailer=mailer,
        existing_account=existing_account,
    )


# --------------------------------------------------------------------------- #
# The acceptance test: one complex, end to end
# --------------------------------------------------------------------------- #


@pytest.mark.integration
@pytest.mark.asyncio
async def test_the_whole_journey_in_one_complex(db_session, async_client, provider_mailer) -> None:
    # 1. An estate admin registers and registers their estate in one step.
    admin, estate_id = await _signup_estate_admin(
        async_client, name=ESTATE_NAME, email=ADMIN_EMAIL
    )
    assert estate_id > 0

    # 2. Bulk units: all or nothing, two of them.
    unit_ids = await _add_units(async_client, admin, estate_id, ("A-1", "A-2"))
    assert len(unit_ids) == 2

    # ... and a duplicate unit number is refused without creating anything.
    duplicates = await async_client.post(
        f"{BASE}/properties/bulk?estate_id={estate_id}",
        json={
            "units": [
                {"unit_no": "A-3", "street_address": "3 Ridge Close"},
                {"unit_no": "A-1", "street_address": "1 Ridge Close"},
            ]
        },
        headers=admin,
    )
    assert duplicates.status_code == 409, duplicates.text
    properties = await async_client.get(
        f"{BASE}/properties?estate_id={estate_id}", headers=admin
    )
    assert properties.json()["total"] == 2  # A-3 was not created either

    # 3. A join code for the estate.
    code = await _issue_join_code(async_client, admin, estate_id)
    assert len(code) == 10

    # 4. A resident registers and joins against a unit.
    resident = await _signup_resident(async_client, email=RESIDENT_EMAIL)
    joined = await async_client.post(
        f"{BASE}/memberships/join",
        json={"code": code, "unit_no": "A-1"},
        headers=resident,
    )
    assert joined.status_code == 201, joined.text
    assert joined.json()["estate_id"] == estate_id
    assert joined.json()["unit_id"] == unit_ids[0]

    # 5. A provider applies. The application stays pending until the HOA approves
    #    it, and no account exists while the application is waiting.
    await _publish_estate(db_session, estate_id)
    application = await _submit_provider_application(
        async_client,
        admin=admin,
        estate_id=estate_id,
        email=PROVIDER_EMAIL,
        trade="plumber",
    )
    from sqlalchemy import text

    provider_count = await db_session.execute(
        text("SELECT count(*) FROM users WHERE email = :email"),
        {"email": PROVIDER_EMAIL},
    )
    assert provider_count.scalar_one() == 0
    pending = await async_client.get(
        f"{BASE}/provider-applications?estate_id={estate_id}&status=pending",
        headers=admin,
    )
    assert pending.status_code == 200, pending.text
    assert pending.json()[0]["application_id"] == application["application_id"]

    # HOA approval sends a one-time setup link; activating it creates the account
    # and its estate membership together.
    provider = await _approve_provider_application(
        async_client,
        admin=admin,
        estate_id=estate_id,
        application=application,
        email=PROVIDER_EMAIL,
        mailer=provider_mailer,
    )
    assert (
        await async_client.get(f"{BASE}/providers/me", headers=provider)
    ).status_code == 200

    # The provider now sees the estate in their own list.
    after = await async_client.get(f"{BASE}/auth/estates", headers=provider)
    assert [e["estate_id"] for e in after.json()["estates"]] == [estate_id]
    assert after.json()["estates"][0]["is_estate_provider"] is True

    # 7. The admin's directory shows exactly that provider, with contact details.
    directory = await async_client.get(
        f"{BASE}/providers?estate_id={estate_id}", headers=admin
    )
    assert directory.status_code == 200, directory.text
    assert directory.json()["total"] == 1
    listed = directory.json()["items"][0]
    provider_id = listed["id"]
    assert listed["email"] == PROVIDER_EMAIL
    assert listed["phone"] == "082 123 4567"

    # 8. The resident files a complaint against their own unit.
    complaint = await async_client.post(
        f"{BASE}/complaints?estate_id={estate_id}",
        json={
            "unit_id": unit_ids[0],
            "category": "water",
            "priority": "high",
            "description": "Burst pipe under the kitchen sink",
        },
        headers=resident,
    )
    assert complaint.status_code == 201, complaint.text
    complaint_id = complaint.json()["id"]
    assert complaint.json()["status"] == "submitted"

    # A work order cannot exist before the complaint has been reviewed.
    early = await async_client.post(
        f"{BASE}/work-orders?estate_id={estate_id}",
        json={"complaint_id": complaint_id, "provider_id": provider_id},
        headers=admin,
    )
    assert early.status_code == 409, early.text

    # 9. The admin reviews it.
    reviewed = await async_client.patch(
        f"{BASE}/complaints/{complaint_id}/status?estate_id={estate_id}",
        json={"status": "reviewed", "note": "Inspected, needs a plumber"},
        headers=admin,
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "reviewed"

    # 10. The admin assigns the provider: one work order, complaint -> assigned.
    created = await async_client.post(
        f"{BASE}/work-orders?estate_id={estate_id}",
        json={"complaint_id": complaint_id, "provider_id": provider_id, "job_cost": "1850.00"},
        headers=admin,
    )
    assert created.status_code == 201, created.text
    work_order_id = created.json()["id"]
    assert created.json()["status"] == "assigned"

    assigned = await async_client.get(
        f"{BASE}/complaints/{complaint_id}?estate_id={estate_id}", headers=admin
    )
    assert assigned.json()["status"] == "assigned"

    # 11. The resident sees the work order on their own complaint.
    seen = await async_client.get(
        f"{BASE}/complaints/{complaint_id}/work-order?estate_id={estate_id}",
        headers=resident,
    )
    assert seen.status_code == 200, seen.text
    assert seen.json()["id"] == work_order_id
    assert seen.json()["provider_id"] == provider_id

    # 12. The provider sees the same job in their own list.
    mine = await async_client.get(
        f"{BASE}/work-orders/mine?estate_id={estate_id}", headers=provider
    )
    assert mine.status_code == 200, mine.text
    assert mine.json()["total"] == 1
    assert mine.json()["items"][0]["id"] == work_order_id

    # 13. The provider starts and completes the work.
    started = await async_client.patch(
        f"{BASE}/work-orders/{work_order_id}?estate_id={estate_id}",
        json={"status": "in_progress"},
        headers=provider,
    )
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "in_progress"

    completed = await async_client.patch(
        f"{BASE}/work-orders/{work_order_id}?estate_id={estate_id}",
        json={"status": "completed", "completion_notes": "Replaced the joint and the pipe run"},
        headers=provider,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"

    # 14. Completing the work resolves the complaint.
    resolved = await async_client.get(
        f"{BASE}/complaints/{complaint_id}?estate_id={estate_id}", headers=resident
    )
    assert resolved.json()["status"] == "resolved"

    # 15. The resident rates the completed job, and that closes the complaint.
    rated = await async_client.post(
        f"{BASE}/work-orders/{work_order_id}/rating?estate_id={estate_id}",
        json={"rating": 5},
        headers=resident,
    )
    assert rated.status_code == 200, rated.text
    assert rated.json()["resident_rating"] == 5

    closed = await async_client.get(
        f"{BASE}/complaints/{complaint_id}?estate_id={estate_id}", headers=resident
    )
    assert closed.json()["status"] == "rated"

    # 16. The member list is exactly the three people who are in this estate.
    members = await async_client.get(
        f"{BASE}/memberships?estate_id={estate_id}", headers=admin
    )
    assert members.status_code == 200, members.text
    assert members.json()["total"] == 3
    rows = members.json()["items"]
    assert {row["role"] for row in rows} == {"hoa_admin", "resident", "service_provider"}
    by_role = {row["role"]: row for row in rows}
    assert by_role["resident"]["unit_no"] == "A-1"
    assert by_role["resident"]["email"] == RESIDENT_EMAIL
    assert by_role["service_provider"]["email"] == PROVIDER_EMAIL
    assert by_role["service_provider"]["unit_no"] is None

    # 17. The admin recalculates the Living Score, and the latest read reflects it.
    recalculated = await async_client.post(
        f"{BASE}/analytics/living-score/recalculate?estate_id={estate_id}", headers=admin
    )
    assert recalculated.status_code == 201, recalculated.text
    snapshot = recalculated.json()

    latest = await async_client.get(
        f"{BASE}/analytics/living-score?estate_id={estate_id}", headers=admin
    )
    assert latest.status_code == 200, latest.text
    assert latest.json()["id"] == snapshot["id"]
    assert latest.json()["as_of"] == snapshot["as_of"]
    assert latest.json()["overall_score"] == snapshot["overall_score"]
    assert latest.json()["engine_version"] == snapshot["engine_version"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_member_of_another_estate_is_denied_at_every_step(
    db_session, async_client, provider_mailer
) -> None:
    # Estate A, fully populated, and estate B beside it.
    admin_a, estate_a = await _signup_estate_admin(
        async_client, name=ESTATE_NAME, email=ADMIN_EMAIL
    )
    units_a = await _add_units(async_client, admin_a, estate_a, ("A-1",))
    code_a = await _issue_join_code(async_client, admin_a, estate_a)
    resident_a = await _signup_resident(async_client, email=RESIDENT_EMAIL)
    assert (
        await async_client.post(
            f"{BASE}/memberships/join",
            json={"code": code_a, "unit_no": "A-1"},
            headers=resident_a,
        )
    ).status_code == 201
    provider_a = await _apply_provider(
        db_session,
        async_client,
        admin=admin_a,
        estate_id=estate_a,
        email=PROVIDER_EMAIL,
        trade="plumber",
        mailer=provider_mailer,
    )
    directory = await async_client.get(f"{BASE}/providers?estate_id={estate_a}", headers=admin_a)
    provider_id_a = directory.json()["items"][0]["id"]

    complaint_a = (
        await async_client.post(
            f"{BASE}/complaints?estate_id={estate_a}",
            json={
                "unit_id": units_a[0],
                "category": "water",
                "description": "Estate A complaint",
            },
            headers=resident_a,
        )
    ).json()
    complaint_id_a = complaint_a["id"]
    assert (
        await async_client.patch(
            f"{BASE}/complaints/{complaint_id_a}/status?estate_id={estate_a}",
            json={"status": "reviewed"},
            headers=admin_a,
        )
    ).status_code == 200
    work_order_a = (
        await async_client.post(
            f"{BASE}/work-orders?estate_id={estate_a}",
            json={"complaint_id": complaint_id_a, "provider_id": provider_id_a},
            headers=admin_a,
        )
    ).json()
    work_order_id_a = work_order_a["id"]

    admin_b, estate_b = await _signup_estate_admin(
        async_client, name=OTHER_ESTATE_NAME, email=OTHER_ADMIN_EMAIL
    )
    units_b = await _add_units(async_client, admin_b, estate_b, ("B-1",))
    code_b = await _issue_join_code(async_client, admin_b, estate_b)
    resident_b = await _signup_resident(async_client, email=OTHER_RESIDENT_EMAIL)
    assert (
        await async_client.post(
            f"{BASE}/memberships/join",
            json={"code": code_b, "unit_no": "B-1"},
            headers=resident_b,
        )
    ).status_code == 201
    provider_b = await _apply_provider(
        db_session,
        async_client,
        admin=admin_b,
        estate_id=estate_b,
        email=OTHER_PROVIDER_EMAIL,
        trade="electrician",
        mailer=provider_mailer,
    )

    # Estate B's admin is not a member of estate A: every admin action there is 403.
    admin_denials = [
        await async_client.get(f"{BASE}/memberships?estate_id={estate_a}", headers=admin_b),
        await async_client.get(
            f"{BASE}/provider-applications?estate_id={estate_a}",
            headers=admin_b,
        ),
        await async_client.get(f"{BASE}/providers?estate_id={estate_a}", headers=admin_b),
        await async_client.get(f"{BASE}/providers/{provider_id_a}?estate_id={estate_a}", headers=admin_b),
        await async_client.get(f"{BASE}/join-codes/current?estate_id={estate_a}", headers=admin_b),
        await async_client.post(f"{BASE}/join-codes?estate_id={estate_a}", json={}, headers=admin_b),
        await async_client.patch(
            f"{BASE}/complaints/{complaint_id_a}/status?estate_id={estate_a}",
            json={"status": "reviewed"},
            headers=admin_b,
        ),
        await async_client.post(
            f"{BASE}/work-orders?estate_id={estate_a}",
            json={"complaint_id": complaint_id_a, "provider_id": provider_id_a},
            headers=admin_b,
        ),
        await async_client.post(
            f"{BASE}/analytics/living-score/recalculate?estate_id={estate_a}", headers=admin_b
        ),
    ]
    assert [response.status_code for response in admin_denials] == [403] * len(admin_denials)

    # Estate B's resident cannot reach estate A's complaints or work.
    resident_denials = [
        await async_client.post(
            f"{BASE}/complaints?estate_id={estate_a}",
            json={"unit_id": units_a[0], "category": "water", "description": "Not my estate"},
            headers=resident_b,
        ),
        await async_client.get(f"{BASE}/complaints?estate_id={estate_a}", headers=resident_b),
        await async_client.get(
            f"{BASE}/complaints/{complaint_id_a}?estate_id={estate_a}", headers=resident_b
        ),
        await async_client.get(
            f"{BASE}/complaints/{complaint_id_a}/work-order?estate_id={estate_a}",
            headers=resident_b,
        ),
        await async_client.get(
            f"{BASE}/work-orders/{work_order_id_a}?estate_id={estate_a}", headers=resident_b
        ),
        await async_client.post(
            f"{BASE}/work-orders/{work_order_id_a}/rating?estate_id={estate_a}",
            json={"rating": 1},
            headers=resident_b,
        ),
    ]
    assert [response.status_code for response in resident_denials] == [403] * len(
        resident_denials
    )

    # The join code is deliberately the whole proof of the right to join, so a
    # resident of another estate who has been *given* estate A's code may join -
    # that is what the code is for. What they cannot do is guess one: an unusable
    # code is a uniform 404 that reveals nothing about the estate.
    guessed = await async_client.post(
        f"{BASE}/memberships/join", json={"code": "ZZZZZZZZZZ", "unit_no": "A-1"}, headers=resident_b
    )
    assert guessed.status_code == 404, guessed.text
    wrong_unit = await async_client.post(
        f"{BASE}/memberships/join", json={"code": code_a, "unit_no": "A-9"}, headers=resident_b
    )
    assert wrong_unit.status_code == 404, wrong_unit.text

    # Estate B's provider cannot list, start or complete estate A's work.
    provider_denials = [
        await async_client.get(f"{BASE}/work-orders/mine?estate_id={estate_a}", headers=provider_b),
        await async_client.get(
            f"{BASE}/work-orders/{work_order_id_a}?estate_id={estate_a}", headers=provider_b
        ),
        await async_client.patch(
            f"{BASE}/work-orders/{work_order_id_a}?estate_id={estate_a}",
            json={"status": "in_progress"},
            headers=provider_b,
        ),
    ]
    assert [response.status_code for response in provider_denials] == [403] * len(
        provider_denials
    )

    # And an object that belongs to another estate is a 404, not a 403: the
    # estate-scoped lookup never confirms that row exists.
    foreign_unit = await async_client.get(
        f"{BASE}/properties/{units_b[0]}?estate_id={estate_a}", headers=admin_a
    )
    assert foreign_unit.status_code == 404, foreign_unit.text

    # Nothing in B's denials left a mark on A.
    work_order_after = await async_client.get(
        f"{BASE}/work-orders/{work_order_id_a}?estate_id={estate_a}", headers=admin_a
    )
    assert work_order_after.json()["status"] == "assigned"
    complaint_after = await async_client.get(
        f"{BASE}/complaints/{complaint_id_a}?estate_id={estate_a}", headers=admin_a
    )
    assert complaint_after.json()["status"] == "assigned"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_provider_directory_is_scoped_to_the_estate_and_the_admin(
    db_session, async_client, provider_mailer
) -> None:
    admin_a, estate_a = await _signup_estate_admin(
        async_client, name=ESTATE_NAME, email=ADMIN_EMAIL
    )
    admin_b, estate_b = await _signup_estate_admin(
        async_client, name=OTHER_ESTATE_NAME, email=OTHER_ADMIN_EMAIL
    )
    provider_a = await _apply_provider(
        db_session,
        async_client,
        admin=admin_a,
        estate_id=estate_a,
        email=PROVIDER_EMAIL,
        trade="plumber",
        mailer=provider_mailer,
    )
    provider_b = await _apply_provider(
        db_session,
        async_client,
        admin=admin_b,
        estate_id=estate_b,
        email=OTHER_PROVIDER_EMAIL,
        trade="electrician",
        mailer=provider_mailer,
    )

    # Each admin sees only their own estate's provider.
    listing_a = await async_client.get(f"{BASE}/providers?estate_id={estate_a}", headers=admin_a)
    listing_b = await async_client.get(f"{BASE}/providers?estate_id={estate_b}", headers=admin_b)
    assert listing_a.json()["total"] == 1
    assert listing_b.json()["total"] == 1
    assert listing_a.json()["items"][0]["email"] == PROVIDER_EMAIL
    assert listing_b.json()["items"][0]["email"] == OTHER_PROVIDER_EMAIL

    # The trade filter still works inside the estate scope.
    filtered = await async_client.get(
        f"{BASE}/providers?estate_id={estate_a}&trade=electrician", headers=admin_a
    )
    assert filtered.json()["total"] == 0

    # Estate B's provider id, read inside estate A, is a 404.
    provider_b_id = listing_b.json()["items"][0]["id"]
    cross = await async_client.get(
        f"{BASE}/providers/{provider_b_id}?estate_id={estate_a}", headers=admin_a
    )
    assert cross.status_code == 404, cross.text

    # A resident is not an admin of the estate: no directory for them.
    code = await _issue_join_code(async_client, admin_a, estate_a)
    assert (
        await async_client.post(
            f"{BASE}/properties/bulk?estate_id={estate_a}",
            json={"units": [{"unit_no": "A-1", "street_address": "1 Ridge Close"}]},
            headers=admin_a,
        )
    ).status_code == 201
    resident = await _signup_resident(async_client, email=RESIDENT_EMAIL)
    assert (
        await async_client.post(
            f"{BASE}/memberships/join",
            json={"code": code, "unit_no": "A-1"},
            headers=resident,
        )
    ).status_code == 201
    denied = await async_client.get(f"{BASE}/providers?estate_id={estate_a}", headers=resident)
    assert denied.status_code == 403, denied.text

    # A provider reads their own profile through /providers/me, and no other.
    own = await async_client.get(f"{BASE}/providers/me", headers=provider_a)
    assert own.status_code == 200, own.text
    assert own.json()["email"] == PROVIDER_EMAIL
    assert own.json()["phone"] == "082 123 4567"
    # ... and a resident has no provider profile to read at all.
    assert (
        await async_client.get(f"{BASE}/providers/me", headers=resident)
    ).status_code == 403
    # ... and a provider who is not in an estate cannot read the directory of one.
    assert (
        await async_client.get(f"{BASE}/providers?estate_id={estate_a}", headers=provider_b)
    ).status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_provider_reviews_require_a_shared_estate(
    db_session, async_client, provider_mailer
) -> None:
    admin, estate_id = await _signup_estate_admin(
        async_client, name=ESTATE_NAME, email=ADMIN_EMAIL
    )
    other_admin, other_estate_id = await _signup_estate_admin(
        async_client, name=OTHER_ESTATE_NAME, email=OTHER_ADMIN_EMAIL
    )
    await _add_units(async_client, admin, estate_id, ("A-1", "A-2"))
    code = await _issue_join_code(async_client, admin, estate_id)
    resident = await _signup_resident(async_client, email=RESIDENT_EMAIL)
    assert (
        await async_client.post(
            f"{BASE}/memberships/join",
            json={"code": code, "unit_no": "A-1"},
            headers=resident,
        )
    ).status_code == 201

    # A provider approved by a different estate cannot be reviewed here.
    await _apply_provider(
        db_session,
        async_client,
        admin=other_admin,
        estate_id=other_estate_id,
        email=PROVIDER_EMAIL,
        trade="plumber",
        mailer=provider_mailer,
    )
    from sqlalchemy import text

    provider_id = (
        await db_session.execute(
            text("SELECT provider_id FROM service_providers WHERE email = :email"),
            {"email": PROVIDER_EMAIL},
        )
    ).scalar_one()

    # The reviews routes are legacy-gated off by default, so this exercises the
    # service rule directly (the route's own gate is unchanged).
    from app.identity.repositories.user_repository import UserRepository
    from app.providers.services.review_service import ReviewService
    from app.core.exceptions import NotFoundException
    from app.providers.schemas.review import ReviewCreate

    resident_user = await UserRepository(db_session).get_by_email(RESIDENT_EMAIL)
    assert resident_user is not None
    service = ReviewService(db_session)
    with pytest.raises(NotFoundException):
        await service.create_review(
            provider_id, ReviewCreate(rating=5, comment="Never met them"), resident_user
        )

    # The provider applies to estate A, and only that HOA's approval unlocks it.
    await _apply_provider(
        db_session,
        async_client,
        admin=admin,
        estate_id=estate_id,
        email=PROVIDER_EMAIL,
        trade="plumber",
        mailer=provider_mailer,
        existing_account=True,
    )
    review = await service.create_review(
        provider_id, ReviewCreate(rating=5, comment="Fixed it properly"), resident_user
    )
    assert review.rating == 5
    assert review.provider_id == provider_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_provider_applications_require_public_estate_and_remain_pending_until_review(
    db_session, async_client
) -> None:
    admin, estate_id = await _signup_estate_admin(
        async_client, name=ESTATE_NAME, email=ADMIN_EMAIL
    )

    private_application = await async_client.post(
        f"{BASE}/provider-applications",
        json={
            "estate_id": estate_id,
            "full_name": "Provider One",
            "email": PROVIDER_EMAIL,
            "trade": "plumber",
            "phone": "082 123 4567",
        },
    )
    assert private_application.status_code == 404

    await _publish_estate(db_session, estate_id)
    application = await _submit_provider_application(
        async_client,
        admin=admin,
        estate_id=estate_id,
        email=PROVIDER_EMAIL,
        trade="plumber",
    )
    duplicate = await async_client.post(
        f"{BASE}/provider-applications",
        json={
            "estate_id": estate_id,
            "full_name": "Provider One",
            "email": PROVIDER_EMAIL,
            "trade": "plumber",
            "phone": "082 123 4567",
        },
    )
    assert duplicate.status_code == 409
    from sqlalchemy import text

    user_count = await db_session.execute(
        text("SELECT count(*) FROM users WHERE email = :email"),
        {"email": PROVIDER_EMAIL},
    )
    assert user_count.scalar_one() == 0
    pending = await async_client.get(
        f"{BASE}/provider-applications?estate_id={estate_id}&status=pending",
        headers=admin,
    )
    assert pending.json()[0]["application_id"] == application["application_id"]


# --------------------------------------------------------------------------- #
# Policy tests that need no database
# --------------------------------------------------------------------------- #


def test_provider_application_request_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ProviderApplicationCreateRequest.model_validate(
            {
                "estate_id": 1,
                "full_name": "Provider One",
                "email": PROVIDER_EMAIL,
                "trade": "plumber",
                "phone": "082 123 4567",
                "role": "service_provider",
            }
        )
    with pytest.raises(ValidationError):
        ProviderApplicationCreateRequest.model_validate(
            {
                "estate_id": 1,
                "full_name": "Provider One",
                "email": "not-an-email",
                "trade": "plumber",
                "phone": "082 123 4567",
            }
        )
    parsed = ProviderApplicationCreateRequest.model_validate(
        {
            "estate_id": 1,
            "full_name": "Provider One",
            "email": PROVIDER_EMAIL,
            "trade": "plumber",
            "phone": "082 123 4567",
        }
    )
    assert str(parsed.email) == PROVIDER_EMAIL


def test_the_limiter_message_is_configurable() -> None:
    limiter = JoinAttemptLimiter(max_failures=1, window_seconds=60)
    limiter.record_failure(7)
    with pytest.raises(RateLimitException) as default_error:
        limiter.ensure_allowed(7)
    assert "join attempts" in default_error.value.detail

    limiter.reset(7)
    limiter.record_failure(7)
    with pytest.raises(RateLimitException) as custom_error:
        limiter.ensure_allowed(7, message="Too many unsuccessful join-code attempts.")
    assert custom_error.value.detail == "Too many unsuccessful join-code attempts."


def test_generated_passwords_are_random_and_readable() -> None:
    first = rp.generate_password()
    second = rp.generate_password()
    assert first != second
    assert len(first.split("-")) == 4
    assert all(len(group) == 5 for group in first.split("-"))
    assert all(char in rp.PASSWORD_ALPHABET for char in first.replace("-", ""))


class _OperatorResult:
    def __init__(self, user):
        self._user = user

    def scalar_one_or_none(self):
        return self._user


class _OperatorSession:
    def __init__(self, user):
        self._user = user
        self.commits = 0

    async def execute(self, _stmt):
        return _OperatorResult(self._user)

    async def commit(self):
        self.commits += 1


def _operator_factory(session):
    @asynccontextmanager
    async def factory():
        yield session

    return factory


def _operator():
    return SimpleNamespace(
        user_id=42, email="ops@example.com", role="resident", password_hash="old-hash"
    )


@pytest.mark.asyncio
async def test_reset_password_dry_run_changes_nothing(monkeypatch, capsys) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/valora_pilot")
    user = _operator()
    session = _OperatorSession(user)

    code = await rp.main(
        ["--email", "ops@example.com"], session_factory=_operator_factory(session)
    )

    output = capsys.readouterr().out
    assert code == 0
    assert user.password_hash == "old-hash"
    assert session.commits == 0
    assert "dry-run" in output
    assert "localhost:5432/valora_pilot" in output
    assert "u:p" not in output  # the printed target is redacted


@pytest.mark.asyncio
async def test_reset_password_apply_prints_the_password_once(monkeypatch, capsys) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/valora_pilot")
    user = _operator()
    session = _OperatorSession(user)

    code = await rp.main(
        ["--email", "ops@example.com", "--apply"],
        session_factory=_operator_factory(session),
    )

    output = capsys.readouterr().out
    assert code == 0
    assert session.commits == 1
    assert user.password_hash != "old-hash"

    printed = [line for line in output.splitlines() if line.strip().startswith("password")]
    assert len(printed) == 1
    password = printed[0].split(":", 1)[1].strip()
    assert verify_password(password, user.password_hash)
    # The new password appears exactly once in the whole run.
    assert output.count(password) == 1


@pytest.mark.asyncio
async def test_reset_password_missing_account_is_an_error(monkeypatch, capsys) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/valora_pilot")
    session = _OperatorSession(None)

    code = await rp.main(
        ["--email", "nobody@example.com", "--apply"],
        session_factory=_operator_factory(session),
    )

    assert code == 1
    assert session.commits == 0
    assert "no account exists" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_reset_password_guards_the_target_database(monkeypatch, capsys) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/valora_demo")
    user = _operator()
    session = _OperatorSession(user)

    refused = await rp.main(
        ["--email", "ops@example.com", "--apply"],
        session_factory=_operator_factory(session),
    )
    assert refused == 1
    assert user.password_hash == "old-hash"
    assert "looks like a demo database" in capsys.readouterr().out

    mismatched = await rp.main(
        ["--email", "ops@example.com", "--apply", "--expect-database", "valora_pilot"],
        session_factory=_operator_factory(session),
    )
    assert mismatched == 1
    assert "--expect-database" in capsys.readouterr().out

    explicit = await rp.main(
        [
            "--email",
            "ops@example.com",
            "--apply",
            "--expect-database",
            "valora_demo",
            "--allow-demo-database",
        ],
        session_factory=_operator_factory(session),
    )
    assert explicit == 0
    assert session.commits == 1


@pytest.mark.asyncio
async def test_reset_password_requires_a_target(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(rp.OperatorError):
        rp.target_database_url()
