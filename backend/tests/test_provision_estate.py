"""Tests for the pilot estate provisioning script (BATCH PILOT-1).

No database is touched: the CLI is driven through an injected fake session that
records every write, so "dry-run writes nothing" and "apply is idempotent" are
real assertions about the script's behaviour rather than about a database.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import provision_estate as prov  # noqa: E402

ESTATE_FILE = {
    "estate": {
        "name": "Ridgeview Pilot Estate",
        "suburb": "Centurion",
        "city": "Pretoria",
        "province": "Gauteng",
        "description": "A real pilot estate.",
    },
    "units": [
        {
            "unit_no": "PL-01",
            "complex_name": "Ridgeview",
            "street_address": "1 Pilot Close",
            "suburb": "Centurion",
            "size_m2": 142.0,
            "bedrooms": 3,
            "bathrooms": 2,
        },
        {
            "unit_no": "PL-02",
            "complex_name": "Ridgeview",
            "street_address": "2 Pilot Close",
            "suburb": "Centurion",
            "size_m2": 118.0,
            "bedrooms": 3,
            "bathrooms": 2,
        },
    ],
    "hoa_admins": [{"email": "chair@ridgeview.test", "full_name": "Ada Chair"}],
    "service_providers": [
        {
            "email": "plumber@ridgeview.test",
            "full_name": "Piet Plumber",
            "trade": "plumbing",
            "phone": "0821110001",
            "emergency_available": True,
        }
    ],
}


# ------------------------------------------------------------------- fakes


class FakeResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class FakeSession:
    """A tiny in-memory store: enough for the provisioning write path."""

    _COUNTERS = {
        "Estate": "estate_id",
        "User": "user_id",
        "Property": "unit_id",
        "ServiceProvider": "provider_id",
        "EstateMembership": "membership_id",
    }

    def __init__(self, rows=None, table_names=()):
        self.rows: list[object] = list(rows or [])
        self._table_names = set(table_names)
        self.adds = 0
        self.add_alls = 0
        self.flushes = 0
        self.commits = 0
        self.rollbacks = 0
        self._next_id = 100

    # write side
    def add(self, instance):
        self.adds += 1
        self.rows.append(instance)

    def add_all(self, instances):
        self.add_alls += 1
        self.rows.extend(instances)

    async def flush(self):
        self.flushes += 1
        for row in self.rows:
            pk = self._COUNTERS.get(type(row).__name__)
            if pk and getattr(row, pk, None) is None:
                self._next_id += 1
                setattr(row, pk, self._next_id)

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1

    async def execute(self, statement, *args, **kwargs):
        """Behave like a tiny database for simple single-entity selects."""
        entity = None
        descriptions = getattr(statement, "column_descriptions", None)
        if descriptions:
            entity = descriptions[0].get("entity")
        if entity is None:
            return FakeResult([])
        return FakeResult([row for row in self.rows if isinstance(row, entity)])

    def written(self, name):
        return [row for row in self.rows if type(row).__name__ == name]


class FakeSessionFactory:
    def __init__(self, rows=None, table_names=()):
        self.session = FakeSession(rows=rows, table_names=table_names)
        self.opened = 0

    def __call__(self):
        self.opened += 1
        return _Ctx(self.session)


class _Ctx:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc):
        return False


def write_estate_file(tmp_path: Path, payload: dict | None = None) -> Path:
    path = tmp_path / "estate.json"
    path.write_text(json.dumps(payload or ESTATE_FILE), encoding="utf-8")
    return path


def fake_hasher(record: list | None = None):
    """A cheap stand-in for bcrypt that never embeds the plaintext."""

    def _hash(password: str) -> str:
        if record is not None:
            record.append(password)
        return "hashed::" + hashlib.sha256(password.encode("utf-8")).hexdigest()

    return _hash


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://pilot_user:s3cret@localhost:5432/valora_pilot",
    )
    monkeypatch.setenv("SECRET_KEY", "test-secret-not-for-production-0123456789")
    monkeypatch.setattr(prov, "hash_password", fake_hasher())
    return monkeypatch


def args_for(*argv: str) -> list[str]:
    return list(argv)


# --------------------------------------------------------------- dry run


@pytest.mark.asyncio
async def test_dry_run_writes_nothing(tmp_path, env, capsys) -> None:
    factory = FakeSessionFactory()
    path = write_estate_file(tmp_path)

    exit_code = await prov.main(
        args_for("estate", "--file", str(path)), session_factory=factory
    )

    out = capsys.readouterr().out
    assert exit_code == 0
    assert factory.session.adds == 0
    assert factory.session.add_alls == 0
    assert factory.session.flushes == 0
    assert factory.session.commits == 0
    assert "dry-run" in out.lower()
    # The plan is still shown, so the operator can review it.
    assert "Ridgeview Pilot Estate" in out
    assert "PL-01" in out


@pytest.mark.asyncio
async def test_target_database_is_printed_first_without_the_password(tmp_path, env, capsys) -> None:
    factory = FakeSessionFactory()
    path = write_estate_file(tmp_path)

    await prov.main(args_for("estate", "--file", str(path)), session_factory=factory)

    first_line = capsys.readouterr().out.splitlines()[0]
    assert "localhost" in first_line
    assert "valora_pilot" in first_line
    assert "s3cret" not in first_line
    assert "pilot_user" not in first_line


@pytest.mark.asyncio
async def test_dry_run_never_prints_a_password(tmp_path, env, capsys) -> None:
    factory = FakeSessionFactory()
    path = write_estate_file(tmp_path)

    await prov.main(args_for("estate", "--file", str(path)), session_factory=factory)

    out = capsys.readouterr().out
    assert "hashed::" not in out
    for word in out.split():
        assert not word.startswith("pwd-")


# --------------------------------------------------------------- apply


@pytest.mark.asyncio
async def test_apply_creates_the_estate_units_people_and_memberships(tmp_path, env, capsys) -> None:
    factory = FakeSessionFactory()
    path = write_estate_file(tmp_path)

    exit_code = await prov.main(
        args_for("estate", "--file", str(path), "--apply"), session_factory=factory
    )

    session = factory.session
    assert exit_code == 0
    assert session.commits == 1

    (estate,) = session.written("Estate")
    assert estate.name == "Ridgeview Pilot Estate"
    assert estate.is_demo is False
    assert estate.estate_id is not None

    units = session.written("Property")
    assert [u.unit_no for u in units] == ["PL-01", "PL-02"]
    assert {u.estate_id for u in units} == {estate.estate_id}

    users = {u.email: u for u in session.written("User")}
    assert users["chair@ridgeview.test"].role == "hoa_admin"
    assert users["plumber@ridgeview.test"].role == "service_provider"
    for user in users.values():
        assert user.password_hash and not user.password_hash.startswith("pwd-")

    (profile,) = session.written("ServiceProvider")
    assert profile.email == "plumber@ridgeview.test"
    assert profile.user_id == users["plumber@ridgeview.test"].user_id
    assert profile.trade == "plumbing"

    memberships = session.written("EstateMembership")
    scopes = {(m.user_id, m.membership_role, m.property_id) for m in memberships}
    assert (users["chair@ridgeview.test"].user_id, "hoa_admin", None) in scopes
    assert (users["plumber@ridgeview.test"].user_id, "service_provider", None) in scopes
    assert {m.estate_id for m in memberships} == {estate.estate_id}


@pytest.mark.asyncio
async def test_provisioned_roles_satisfy_the_existing_authorization_rules(tmp_path, env) -> None:
    """The rows we write must pass the real estate authorization service."""
    from app.identity.services.estate_authorization_service import EstateAuthorizationService

    factory = FakeSessionFactory()
    path = write_estate_file(tmp_path)
    await prov.main(args_for("estate", "--file", str(path), "--apply"), session_factory=factory)

    session = factory.session
    users = {u.email: u for u in session.written("User")}
    memberships = session.written("EstateMembership")

    class FakeMembershipRepo:
        async def list_for_user_and_estate(self, *, user_id: int, estate_id: int):
            return [m for m in memberships if m.user_id == user_id and m.estate_id == estate_id]

        async def get_for_user_and_estate(self, *, user_id: int, estate_id: int):
            matches = await self.list_for_user_and_estate(user_id=user_id, estate_id=estate_id)
            return matches[0] if matches else None

    auth = EstateAuthorizationService.__new__(EstateAuthorizationService)
    auth._memberships = FakeMembershipRepo()
    estate_id = memberships[0].estate_id

    admin = users["chair@ridgeview.test"]
    admin_access = await auth.resolve_access(
        SimpleNamespace(user_id=admin.user_id, role=admin.role), estate_id
    )
    assert admin_access.is_estate_admin is True

    # This is exactly what WorkOrderService.create_work_order checks before it
    # will assign work to a provider.
    provider = users["plumber@ridgeview.test"]
    provider_access = await auth.resolve_access(
        SimpleNamespace(user_id=provider.user_id, role=provider.role), estate_id
    )
    assert provider_access.is_estate_provider is True

    # ...and a non-member is refused outright.
    from app.core.exceptions import ForbiddenException

    with pytest.raises(ForbiddenException):
        await auth.resolve_access(SimpleNamespace(user_id=999, role="resident"), estate_id)


@pytest.mark.asyncio
async def test_provider_profile_is_linked_the_way_the_work_order_path_looks_it_up(
    tmp_path, env
) -> None:
    """`WorkOrderService` finds a provider through `get_by_user_id` and refuses a
    profile whose `user_id` is NULL, so the linker must fill it in."""
    from app.providers.repositories.service_provider_repository import (
        ServiceProviderRepository,
    )

    factory = FakeSessionFactory()
    path = write_estate_file(tmp_path)
    await prov.main(
        args_for("estate", "--file", str(path), "--apply"), session_factory=factory
    )

    session = factory.session
    users = {u.email: u for u in session.written("User")}
    (profile,) = session.written("ServiceProvider")
    provider_user = users["plumber@ridgeview.test"]

    assert profile.user_id is not None, "a NULL user_id blocks provider assignment"
    assert profile.user_id == provider_user.user_id
    assert provider_user.role == "service_provider"

    found = await ServiceProviderRepository(session).get_by_user_id(
        provider_user.user_id
    )
    assert found is not None
    assert found.provider_id == profile.provider_id


@pytest.mark.asyncio
async def test_apply_is_idempotent(tmp_path, env, capsys) -> None:
    path = write_estate_file(tmp_path)
    factory = FakeSessionFactory()

    await prov.main(args_for("estate", "--file", str(path), "--apply"), session_factory=factory)
    first_rows = len(factory.session.rows)
    first_commits = factory.session.commits

    exit_code = await prov.main(
        args_for("estate", "--file", str(path), "--apply"), session_factory=factory
    )

    out = capsys.readouterr().out
    assert exit_code == 0
    assert len(factory.session.rows) == first_rows
    assert factory.session.commits == first_commits
    assert "already" in out.lower() or "nothing to do" in out.lower()


# --------------------------------------------------------------- collisions


@pytest.mark.asyncio
async def test_unit_no_owned_by_another_estate_stops(tmp_path, env, capsys) -> None:
    from app.property.models.estate import Estate
    from app.property.models.property import Property

    other = Estate(
        estate_id=7, name="Someone Else", suburb="x", city="x", province="x", is_demo=False
    )
    taken = Property(
        unit_id=70,
        estate_id=7,
        unit_no="PL-01",
        complex_name="Other",
        street_address="x",
    )
    factory = FakeSessionFactory(rows=[other, taken])
    path = write_estate_file(tmp_path)

    exit_code = await prov.main(
        args_for("estate", "--file", str(path), "--apply"), session_factory=factory
    )

    out = capsys.readouterr().out
    assert exit_code != 0
    assert "PL-01" in out
    assert "Someone Else" in out
    assert factory.session.adds == 0
    assert factory.session.commits == 0


@pytest.mark.asyncio
async def test_legacy_unit_with_no_estate_stops(tmp_path, env, capsys) -> None:
    from app.property.models.property import Property

    taken = Property(
        unit_id=71, estate_id=None, unit_no="PL-02", complex_name="Legacy", street_address="x"
    )
    factory = FakeSessionFactory(rows=[taken])
    path = write_estate_file(tmp_path)

    exit_code = await prov.main(
        args_for("estate", "--file", str(path), "--apply"), session_factory=factory
    )

    out = capsys.readouterr().out
    assert exit_code != 0
    assert "PL-02" in out
    assert factory.session.adds == 0


@pytest.mark.asyncio
async def test_duplicate_unit_numbers_in_the_estate_file_stop(tmp_path, env, capsys) -> None:
    payload = json.loads(json.dumps(ESTATE_FILE))
    payload["units"][1]["unit_no"] = "PL-01"
    factory = FakeSessionFactory()
    path = write_estate_file(tmp_path, payload)

    exit_code = await prov.main(
        args_for("estate", "--file", str(path), "--apply"), session_factory=factory
    )

    assert exit_code != 0
    assert "PL-01" in capsys.readouterr().out
    assert factory.session.adds == 0


# --------------------------------------------------------------- passwords


@pytest.mark.asyncio
async def test_passwords_are_printed_once_on_apply_and_never_logged(
    tmp_path, env, capsys, caplog
) -> None:
    env.setattr(prov, "generate_password", lambda *a, **k: "pwd-Deterministic-123456")
    factory = FakeSessionFactory()
    path = write_estate_file(tmp_path)

    with caplog.at_level(logging.DEBUG):
        await prov.main(
            args_for("estate", "--file", str(path), "--apply"), session_factory=factory
        )

    out = capsys.readouterr().out
    assert out.count("pwd-Deterministic-123456") == 2  # one admin, one provider
    assert "chair@ridgeview.test" in out
    assert "pwd-Deterministic-123456" not in caplog.text

    for user in factory.session.written("User"):
        assert "pwd-Deterministic-123456" not in (user.password_hash or "")
        assert (user.password_hash or "").startswith("hashed::")


# --------------------------------------------------------------- safety rails


@pytest.mark.asyncio
async def test_refuses_to_write_into_a_database_that_looks_like_demo(tmp_path, env, capsys) -> None:
    env.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://valora_user:pw@localhost:5432/valora_demo",
    )
    factory = FakeSessionFactory()
    path = write_estate_file(tmp_path)

    exit_code = await prov.main(
        args_for("estate", "--file", str(path), "--apply"), session_factory=factory
    )

    out = capsys.readouterr().out
    assert exit_code != 0
    assert "demo" in out.lower()
    assert factory.session.adds == 0
    assert factory.session.commits == 0


@pytest.mark.asyncio
async def test_expect_database_guard_refuses_the_wrong_target(tmp_path, env, capsys) -> None:
    factory = FakeSessionFactory()
    path = write_estate_file(tmp_path)

    exit_code = await prov.main(
        args_for(
            "estate", "--file", str(path), "--apply", "--expect-database", "valora_pilot_2"
        ),
        session_factory=factory,
    )

    assert exit_code != 0
    assert "valora_pilot" in capsys.readouterr().out
    assert factory.session.adds == 0


@pytest.mark.asyncio
async def test_malformed_estate_file_is_reported_not_crashed(tmp_path, env, capsys) -> None:
    factory = FakeSessionFactory()
    path = write_estate_file(tmp_path, {"estate": {"name": "No units"}})

    exit_code = await prov.main(
        args_for("estate", "--file", str(path), "--apply"), session_factory=factory
    )

    assert exit_code != 0
    assert factory.session.adds == 0


# --------------------------------------------------------------- residents


@pytest.mark.asyncio
async def test_link_resident_creates_a_membership_on_the_unit(tmp_path, env, capsys) -> None:
    from app.identity.models.user import User
    from app.property.models.estate import Estate
    from app.property.models.property import Property

    estate = Estate(
        estate_id=5, name="Ridgeview Pilot Estate", suburb="x", city="x", province="x", is_demo=False
    )
    unit = Property(
        unit_id=50, estate_id=5, unit_no="PL-01", complex_name="R", street_address="x"
    )
    resident = User(
        user_id=9,
        email="res@ridgeview.test",
        full_name="Resident One",
        password_hash="x",
        role="resident",
        unit_no="PL-01",
    )
    factory = FakeSessionFactory(rows=[estate, unit, resident])

    exit_code = await prov.main(
        args_for(
            "link-resident",
            "--estate-id",
            "5",
            "--email",
            "res@ridgeview.test",
            "--unit-no",
            "PL-01",
            "--apply",
        ),
        session_factory=factory,
    )

    assert exit_code == 0
    (membership,) = factory.session.written("EstateMembership")
    assert membership.user_id == 9
    assert membership.estate_id == 5
    assert membership.property_id == 50
    assert membership.membership_role == "resident"


@pytest.mark.asyncio
async def test_link_resident_is_idempotent(tmp_path, env, capsys) -> None:
    from app.identity.models.user import User
    from app.property.models.estate import Estate
    from app.property.models.property import Property

    estate = Estate(estate_id=5, name="R", suburb="x", city="x", province="x", is_demo=False)
    unit = Property(unit_id=50, estate_id=5, unit_no="PL-01", complex_name="R", street_address="x")
    resident = User(
        user_id=9, email="res@ridgeview.test", full_name="R", password_hash="x", role="resident"
    )
    factory = FakeSessionFactory(rows=[estate, unit, resident])
    argv = args_for(
        "link-resident", "--estate-id", "5", "--email", "res@ridgeview.test",
        "--unit-no", "PL-01", "--apply",
    )

    await prov.main(argv, session_factory=factory)
    before = len(factory.session.rows)
    exit_code = await prov.main(argv, session_factory=factory)

    assert exit_code == 0
    assert len(factory.session.rows) == before


@pytest.mark.asyncio
async def test_link_resident_warns_when_the_declared_unit_differs(tmp_path, env, capsys) -> None:
    from app.identity.models.user import User
    from app.property.models.estate import Estate
    from app.property.models.property import Property

    estate = Estate(estate_id=5, name="R", suburb="x", city="x", province="x", is_demo=False)
    unit = Property(unit_id=50, estate_id=5, unit_no="PL-01", complex_name="R", street_address="x")
    resident = User(
        user_id=9,
        email="res@ridgeview.test",
        full_name="R",
        password_hash="x",
        role="resident",
        unit_no="PL-99",  # what the resident typed at registration
    )
    factory = FakeSessionFactory(rows=[estate, unit, resident])

    await prov.main(
        args_for(
            "link-resident", "--estate-id", "5", "--email", "res@ridgeview.test",
            "--unit-no", "PL-01",
        ),
        session_factory=factory,
    )

    out = capsys.readouterr().out
    assert "PL-99" in out and "PL-01" in out
    assert "warn" in out.lower()


@pytest.mark.asyncio
async def test_link_resident_reports_an_unknown_email_and_writes_nothing(tmp_path, env, capsys) -> None:
    from app.property.models.estate import Estate
    from app.property.models.property import Property

    estate = Estate(estate_id=5, name="R", suburb="x", city="x", province="x", is_demo=False)
    unit = Property(unit_id=50, estate_id=5, unit_no="PL-01", complex_name="R", street_address="x")
    factory = FakeSessionFactory(rows=[estate, unit])

    exit_code = await prov.main(
        args_for(
            "link-resident", "--estate-id", "5", "--email", "ghost@ridgeview.test",
            "--unit-no", "PL-01", "--apply",
        ),
        session_factory=factory,
    )

    out = capsys.readouterr().out
    assert exit_code != 0
    assert "ghost@ridgeview.test" in out
    assert factory.session.adds == 0


@pytest.mark.asyncio
async def test_link_residents_csv_reads_email_and_unit_columns(tmp_path, env, capsys) -> None:
    from app.identity.models.user import User
    from app.property.models.estate import Estate
    from app.property.models.property import Property

    estate = Estate(estate_id=5, name="R", suburb="x", city="x", province="x", is_demo=False)
    unit1 = Property(unit_id=50, estate_id=5, unit_no="PL-01", complex_name="R", street_address="x")
    unit2 = Property(unit_id=51, estate_id=5, unit_no="PL-02", complex_name="R", street_address="x")
    users = [
        User(user_id=9, email="a@ridgeview.test", full_name="A", password_hash="x", role="resident"),
        User(user_id=10, email="b@ridgeview.test", full_name="B", password_hash="x", role="resident"),
    ]
    factory = FakeSessionFactory(rows=[estate, unit1, unit2, *users])
    csv_path = tmp_path / "residents.csv"
    csv_path.write_text(
        "email,unit_no\na@ridgeview.test,PL-01\nb@ridgeview.test,PL-02\n", encoding="utf-8"
    )

    exit_code = await prov.main(
        args_for(
            "link-residents-csv", "--estate-id", "5", "--file", str(csv_path), "--apply"
        ),
        session_factory=factory,
    )

    memberships = factory.session.written("EstateMembership")
    assert exit_code == 0
    assert {(m.user_id, m.property_id) for m in memberships} == {(9, 50), (10, 51)}


@pytest.mark.asyncio
async def test_link_residents_csv_reports_a_missing_unit_and_skips_the_row(tmp_path, env, capsys) -> None:
    from app.identity.models.user import User
    from app.property.models.estate import Estate
    from app.property.models.property import Property

    estate = Estate(estate_id=5, name="R", suburb="x", city="x", province="x", is_demo=False)
    unit1 = Property(unit_id=50, estate_id=5, unit_no="PL-01", complex_name="R", street_address="x")
    resident = User(
        user_id=9, email="a@ridgeview.test", full_name="A", password_hash="x", role="resident"
    )
    factory = FakeSessionFactory(rows=[estate, unit1, resident])
    csv_path = tmp_path / "residents.csv"
    csv_path.write_text(
        "email,unit_no\na@ridgeview.test,PL-01\nb@ridgeview.test,PL-77\n", encoding="utf-8"
    )

    exit_code = await prov.main(
        args_for(
            "link-residents-csv", "--estate-id", "5", "--file", str(csv_path), "--apply"
        ),
        session_factory=factory,
    )

    out = capsys.readouterr().out
    memberships = factory.session.written("EstateMembership")
    assert exit_code != 0
    assert "PL-77" in out
    assert {(m.user_id, m.property_id) for m in memberships} == {(9, 50)}


# ------------------------------------------------------- pure helpers


def test_redact_database_url_hides_credentials() -> None:
    redacted = prov.redact_database_url(
        "postgresql+asyncpg://valora_user:valora_password@db.example.com:5432/valora_pilot"
    )
    assert "valora_user" not in redacted
    assert "valora_password" not in redacted
    assert "db.example.com" in redacted
    assert "5432" in redacted
    assert "valora_pilot" in redacted


def test_generated_passwords_are_long_and_unique() -> None:
    passwords = {prov.generate_password() for _ in range(20)}
    assert len(passwords) == 20
    assert all(len(password) >= 16 for password in passwords)


def test_database_name_helper() -> None:
    assert (
        prov.database_name("postgresql+asyncpg://u:p@localhost:5432/valora_pilot")
        == "valora_pilot"
    )
    assert prov.database_name("postgresql+asyncpg://u:p@localhost:5432/valora_pilot?x=1") == "valora_pilot"
