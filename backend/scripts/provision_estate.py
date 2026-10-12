"""Provision a REAL pilot estate, with no seed data.

The pilot runs against its **own** database, separate from the demo database.
This script stands that database up with real people, and it is deliberately
conservative:

* **dry-run by default** - nothing is written unless ``--apply`` is passed;
* the **target database host and name are printed first**, and because the URL is
  read straight from the environment (never from ``.env``) the printed target is
  provably the database this run will use;
* writing into a database whose name looks like a demo/seed database is
  **refused** unless ``--allow-demo-database`` is passed;
* ``--expect-database NAME`` refuses the run when the target is not the database
  the operator meant;
* **idempotent** - a second run creates nothing;
* **unit numbers are never reused** across estates (see the note below);
* passwords are generated with :mod:`secrets`, printed **once** to stdout under
  ``--apply``, and never logged or stored in plain text.

The demo seeder (``app/seed_demo.py``) is not imported, called or modified here.

Estate file format (JSON)::

    {
      "estate": {"name": "...", "suburb": "...", "city": "...", "province": "...",
                 "description": "..."},
      "units": [{"unit_no": "PL-01", "complex_name": "...", "street_address": "...",
                 "suburb": "...", "size_m2": 142.0, "bedrooms": 3, "bathrooms": 2}],
      "hoa_admins": [{"email": "...", "full_name": "..."}],
      "service_providers": [{"email": "...", "full_name": "...", "trade": "plumbing",
                             "phone": "0821110001", "emergency_available": true}]
    }

Usage::

    export DATABASE_URL="postgresql+asyncpg://user:pw@host:5432/valora_pilot"
    python scripts/provision_estate.py estate --file estate.json            # dry run
    python scripts/provision_estate.py estate --file estate.json --apply
    python scripts/provision_estate.py link-resident --estate-id 1 --email a@b.co --unit-no PL-01 --apply
    python scripts/provision_estate.py link-residents-csv --estate-id 1 --file residents.csv --apply

NOTE on unit numbers: the batch that asked for this script said
``Property.unit_no`` is globally unique. In the real tree it is **not** - the
hardening migration (``d4a7e1c9b3f2``) replaced the global unique with
``uq_properties_estate_unit_no`` (per estate) plus a partial unique index for
legacy rows where ``estate_id IS NULL``. This script therefore refuses to reuse a
unit number that exists in *any* other estate, which is stricter than the
database requires and is the safe direction for a pilot. The constraint itself is
never altered.

NOTE on approval flags: neither ``hoa_approved`` nor ``email_verified`` is
checked anywhere in the code today - login verifies the password only. Both are
set to true for provisioned accounts so the API response describes an
operator-provisioned user correctly. See docs/PILOT_RUNBOOK.md.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import os
import secrets
import string
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence
from urllib.parse import urlsplit

# Allow "python scripts/provision_estate.py" from the backend directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.common.enums import UserRole  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.identity.models.estate_membership import EstateMembership  # noqa: E402
from app.identity.models.user import User  # noqa: E402
from app.property.models.estate import Estate  # noqa: E402
from app.property.models.property import Property  # noqa: E402
from app.providers.models.service_provider import ServiceProvider  # noqa: E402

logger = logging.getLogger("provision_estate")

# A target whose name contains one of these is treated as a throwaway database.
DEMO_MARKERS: tuple[str, ...] = ("demo", "seed", "sample", "scratch")
PASSWORD_ALPHABET = string.ascii_letters + string.digits
PASSWORD_LENGTH = 24
LEGACY_UNIT_LABEL = "a legacy row with no estate"


class ProvisionError(Exception):
    """Something the operator must fix before anything is written."""


class CollisionError(ProvisionError):
    """A unit number is already taken; we never duplicate or alter it."""


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #


def database_name(url: str) -> str:
    """The database name inside a SQLAlchemy URL, without query parameters."""
    return urlsplit(url).path.lstrip("/").split("?")[0]


def redact_database_url(url: str) -> str:
    """``host:port/name`` only - never a user name or a password."""
    parts = urlsplit(url)
    host = parts.hostname or "<unknown host>"
    port = f":{parts.port}" if parts.port else ""
    return f"{host}{port}/{database_name(url) or '<unknown database>'}"


def looks_like_a_demo_database(url: str) -> bool:
    name = database_name(url).lower()
    return any(marker in name for marker in DEMO_MARKERS)


def generate_password(length: int = PASSWORD_LENGTH) -> str:
    """A random, high-entropy password. Never logged, never stored in plain text."""
    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))


def target_database_url() -> str:
    """Read the target from the environment.

    Deliberately does **not** fall back to ``.env``: provisioning must be an
    explicit act, and the value printed to the operator is then provably the value
    used to connect.
    """
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise ProvisionError(
            "DATABASE_URL is not set. Export it for this shell "
            "(this script does not read .env, on purpose) and re-run."
        )
    return url


# --------------------------------------------------------------------------- #
# specifications
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class UnitSpec:
    unit_no: str
    complex_name: str
    street_address: str
    suburb: str | None = None
    size_m2: Decimal | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None


@dataclass(frozen=True)
class PersonSpec:
    email: str
    full_name: str


@dataclass(frozen=True)
class ProviderSpec:
    email: str
    full_name: str
    trade: str
    phone: str
    emergency_available: bool = False


@dataclass(frozen=True)
class EstateSpec:
    name: str
    suburb: str
    city: str
    province: str
    description: str | None
    units: tuple[UnitSpec, ...]
    hoa_admins: tuple[PersonSpec, ...]
    service_providers: tuple[ProviderSpec, ...]


@dataclass(frozen=True)
class ResidentRow:
    email: str
    unit_no: str


@dataclass(frozen=True)
class MembershipSpec:
    email: str
    role: str
    unit_no: str | None = None
    user_id: int | None = None
    property_id: int | None = None


def _require(payload: dict[str, Any], key: str, where: str) -> Any:
    if key not in payload or payload[key] in (None, ""):
        raise ProvisionError(f"{where}: '{key}' is required.")
    return payload[key]


def _optional_decimal(value: Any, where: str) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ProvisionError(f"{where}: '{value}' is not a number.") from None


def _optional_int(value: Any, where: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ProvisionError(f"{where}: '{value}' is not a whole number.") from None


def _parse_people(payload: Any, where: str) -> list[PersonSpec]:
    if payload in (None, ""):
        return []
    if not isinstance(payload, list):
        raise ProvisionError(f"estate file: '{where}' must be a list.")
    people: list[PersonSpec] = []
    for index, entry in enumerate(payload):
        label = f"{where}[{index}]"
        if not isinstance(entry, dict):
            raise ProvisionError(f"{label}: must be an object.")
        people.append(
            PersonSpec(
                email=str(_require(entry, "email", label)).strip().lower(),
                full_name=str(_require(entry, "full_name", label)).strip(),
            )
        )
    return people


def _parse_providers(payload: Any) -> list[ProviderSpec]:
    if payload in (None, ""):
        return []
    if not isinstance(payload, list):
        raise ProvisionError("estate file: 'service_providers' must be a list.")
    providers: list[ProviderSpec] = []
    for index, entry in enumerate(payload):
        label = f"service_providers[{index}]"
        if not isinstance(entry, dict):
            raise ProvisionError(f"{label}: must be an object.")
        providers.append(
            ProviderSpec(
                email=str(_require(entry, "email", label)).strip().lower(),
                full_name=str(_require(entry, "full_name", label)).strip(),
                trade=str(_require(entry, "trade", label)).strip(),
                phone=str(_require(entry, "phone", label)).strip(),
                emergency_available=bool(entry.get("emergency_available", False)),
            )
        )
    return providers


def _duplicates(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    repeated: set[str] = set()
    for value in values:
        if value in seen:
            repeated.add(value)
        seen.add(value)
    return sorted(repeated)


def load_estate_spec(path: str | Path) -> EstateSpec:
    """Parse and validate an estate JSON file, failing with a usable message."""
    source = Path(path)
    if not source.is_file():
        raise ProvisionError(f"Estate file not found: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProvisionError(f"Estate file {source} is not valid JSON: {exc}") from None

    estate_payload = _require(payload, "estate", "estate file")
    if not isinstance(estate_payload, dict):
        raise ProvisionError("estate file: 'estate' must be an object.")

    units_payload = payload.get("units")
    if not isinstance(units_payload, list) or not units_payload:
        raise ProvisionError("estate file: 'units' must be a non-empty list.")

    units: list[UnitSpec] = []
    for index, unit in enumerate(units_payload):
        where = f"units[{index}]"
        if not isinstance(unit, dict):
            raise ProvisionError(f"{where}: must be an object.")
        units.append(
            UnitSpec(
                unit_no=str(_require(unit, "unit_no", where)).strip(),
                complex_name=str(_require(unit, "complex_name", where)).strip(),
                street_address=str(_require(unit, "street_address", where)).strip(),
                suburb=(str(unit["suburb"]).strip() if unit.get("suburb") else None),
                size_m2=_optional_decimal(unit.get("size_m2"), where),
                bedrooms=_optional_int(unit.get("bedrooms"), where),
                bathrooms=_optional_int(unit.get("bathrooms"), where),
            )
        )

    admins = _parse_people(payload.get("hoa_admins"), "hoa_admins")
    if not admins:
        raise ProvisionError("estate file: at least one hoa_admin is required.")
    providers = _parse_providers(payload.get("service_providers"))

    repeated_emails = _duplicates(
        [person.email for person in admins] + [p.email for p in providers]
    )
    if repeated_emails:
        raise ProvisionError(
            "estate file: these emails appear more than once: "
            + ", ".join(repeated_emails)
        )
    repeated_units = _duplicates(unit.unit_no for unit in units)
    if repeated_units:
        raise ProvisionError(
            "estate file: these unit numbers appear more than once: "
            + ", ".join(repeated_units)
        )

    return EstateSpec(
        name=str(_require(estate_payload, "name", "estate")).strip(),
        suburb=str(_require(estate_payload, "suburb", "estate")).strip(),
        city=str(_require(estate_payload, "city", "estate")).strip(),
        province=str(_require(estate_payload, "province", "estate")).strip(),
        description=(
            str(estate_payload["description"]).strip()
            if estate_payload.get("description")
            else None
        ),
        units=tuple(units),
        hoa_admins=tuple(admins),
        service_providers=tuple(providers),
    )


def load_residents_csv(path: str | Path) -> list[ResidentRow]:
    """Read a residents CSV with ``email`` and ``unit_no`` columns."""
    source = Path(path)
    if not source.is_file():
        raise ProvisionError(f"Residents CSV not found: {source}")
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = {(name or "").strip().lower() for name in (reader.fieldnames or [])}
        missing = {"email", "unit_no"} - columns
        if missing:
            raise ProvisionError(
                f"{source} must have 'email' and 'unit_no' columns; missing "
                + ", ".join(sorted(missing))
            )
        rows: list[ResidentRow] = []
        for line in reader:
            email = (line.get("email") or "").strip().lower()
            unit_no = (line.get("unit_no") or "").strip()
            if not email and not unit_no:
                continue
            if not email or not unit_no:
                raise ProvisionError(
                    f"{source}: every row needs both an email and a unit_no."
                )
            rows.append(ResidentRow(email=email, unit_no=unit_no))
    if not rows:
        raise ProvisionError(f"{source} has no resident rows.")
    return rows


# --------------------------------------------------------------------------- #
# what already exists
# --------------------------------------------------------------------------- #


@dataclass
class ExistingState:
    estate_id: int | None = None
    estate_names: set[str] = field(default_factory=set)
    unit_ids: dict[str, int] = field(default_factory=dict)
    unit_owner_labels: dict[str, str] = field(default_factory=dict)
    user_ids: dict[str, int] = field(default_factory=dict)
    user_roles: dict[str, str] = field(default_factory=dict)
    user_declared_unit_no: dict[str, str | None] = field(default_factory=dict)
    provider_emails: set[str] = field(default_factory=set)
    membership_roles: set[tuple[int, int, str]] = field(default_factory=set)
    membership_units: set[tuple[int, int]] = field(default_factory=set)

    def linked_units(self, user_id: int) -> list[int]:
        return sorted(
            property_id
            for (member_id, property_id) in self.membership_units
            if member_id == user_id
        )


def summarise_existing(
    *,
    estate_name: str,
    units: Sequence[Any],
    users: Sequence[Any],
    providers: Sequence[Any],
    memberships: Sequence[Any],
    estate_id: int | None = None,
    estate_names_by_id: dict[int, str] | None = None,
) -> ExistingState:
    """Build the existence picture from ORM rows (pure, so it is testable)."""
    names = dict(estate_names_by_id or {})
    state = ExistingState(estate_id=estate_id, estate_names=set(names.values()) | {estate_name})

    for unit in units:
        owner = getattr(unit, "estate_id", None)
        if owner is not None and owner == estate_id:
            state.unit_ids[unit.unit_no] = unit.unit_id
        state.unit_owner_labels[unit.unit_no] = (
            LEGACY_UNIT_LABEL
            if owner is None
            else names.get(owner, f"estate #{owner}")
        )

    for user in users:
        email = (user.email or "").lower()
        state.user_ids[email] = user.user_id
        state.user_roles[email] = user.role
        state.user_declared_unit_no[email] = getattr(user, "unit_no", None)

    for provider in providers:
        state.provider_emails.add((provider.email or "").lower())

    for membership in memberships:
        state.membership_roles.add(
            (membership.user_id, membership.estate_id, membership.membership_role)
        )
        if membership.property_id is not None:
            state.membership_units.add((membership.user_id, membership.property_id))

    return state


async def _summarise_from_session(
    session: AsyncSession, *, estate_id: int | None
) -> ExistingState:
    estates = list((await session.execute(select(Estate))).scalars().all())
    target = next((e for e in estates if e.estate_id == estate_id), None)
    units = list((await session.execute(select(Property))).scalars().all())
    users = list((await session.execute(select(User))).scalars().all())
    providers = list((await session.execute(select(ServiceProvider))).scalars().all())
    memberships = list(
        (
            await session.execute(
                select(EstateMembership).where(EstateMembership.estate_id == estate_id)
            )
        )
        .scalars()
        .all()
    )
    return summarise_existing(
        estate_name=target.name if target is not None else "",
        units=units,
        users=users,
        providers=providers,
        memberships=memberships,
        estate_id=estate_id,
        estate_names_by_id={e.estate_id: e.name for e in estates},
    )


async def load_estate_state(session: AsyncSession, *, estate_name: str) -> ExistingState:
    """Everything the estate planner needs to decide what to create."""
    estates = list((await session.execute(select(Estate))).scalars().all())
    target = next((e for e in estates if e.name == estate_name), None)
    return await _summarise_from_session(
        session, estate_id=target.estate_id if target is not None else None
    )


async def load_unit_state(session: AsyncSession, *, estate_id: int) -> ExistingState:
    """The subset needed to link residents: users, units and memberships."""
    state = await _summarise_from_session(session, estate_id=estate_id)
    if state.estate_id is None:
        raise ProvisionError(f"Estate {estate_id} was not found.")
    return state


# --------------------------------------------------------------------------- #
# planning (pure)
# --------------------------------------------------------------------------- #


@dataclass
class ProvisionPlan:
    create_estate: bool = False
    units: list[UnitSpec] = field(default_factory=list)
    admins: list[PersonSpec] = field(default_factory=list)
    providers: list[tuple[PersonSpec, ProviderSpec]] = field(default_factory=list)
    memberships: list[MembershipSpec] = field(default_factory=list)
    skips: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.creates_anything()

    def creates_anything(self) -> bool:
        return bool(self.create_estate or self.units or self.admins or self.providers)


def plan_estate(spec: EstateSpec, state: ExistingState) -> ProvisionPlan:
    """Decide what to create. Raises on a unit-number collision or a bad state."""
    plan = ProvisionPlan(create_estate=state.estate_id is None)

    if plan.create_estate:
        if spec.name in state.estate_names:
            raise ProvisionError(
                f"An estate named '{spec.name}' already exists but could not be loaded. Stop."
            )
    else:
        plan.skips.append(f"estate '{spec.name}' already exists (#{state.estate_id})")

    collisions: list[str] = []
    for unit in spec.units:
        if unit.unit_no not in state.unit_owner_labels:
            plan.units.append(unit)
        elif state.estate_id is not None and unit.unit_no in state.unit_ids:
            plan.skips.append(f"unit {unit.unit_no} already exists in this estate")
        else:
            collisions.append(
                f"{unit.unit_no} is already the unit number of "
                f"{state.unit_owner_labels[unit.unit_no]}"
            )
    if collisions:
        raise CollisionError(
            "Refusing to run: a unit number must never be duplicated, and these "
            "already exist: " + "; ".join(collisions)
        )

    for admin in spec.hoa_admins:
        known_user_id = state.user_ids.get(admin.email)
        if known_user_id is None:
            plan.admins.append(admin)
        else:
            plan.skips.append(f"user {admin.email} already exists")
        if not _membership_present(state, known_user_id, UserRole.hoa_admin.value):
            plan.memberships.append(
                MembershipSpec(
                    email=admin.email,
                    role=UserRole.hoa_admin.value,
                    user_id=known_user_id,
                )
            )
        else:
            plan.skips.append(f"{admin.email} is already an estate admin")

    for provider in spec.service_providers:
        known_user_id = state.user_ids.get(provider.email)
        if known_user_id is None:
            plan.providers.append(
                (PersonSpec(email=provider.email, full_name=provider.full_name), provider)
            )
        else:
            plan.skips.append(f"user {provider.email} already exists")
        if provider.email in state.provider_emails:
            plan.skips.append(f"provider profile {provider.email} already exists")
        if not _membership_present(
            state, known_user_id, UserRole.service_provider.value
        ):
            plan.memberships.append(
                MembershipSpec(
                    email=provider.email,
                    role=UserRole.service_provider.value,
                    user_id=known_user_id,
                )
            )
        else:
            plan.skips.append(f"{provider.email} is already a service provider")

    return plan


def _membership_present(
    state: ExistingState, user_id: int | None, role: str
) -> bool:
    """A membership exists if we already hold the row for this user, estate and role."""
    if user_id is None or state.estate_id is None:
        return False
    return (user_id, state.estate_id, role) in state.membership_roles


@dataclass
class ResidentPlan:
    links: list[MembershipSpec] = field(default_factory=list)
    skips: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def plan_residents(
    rows: Sequence[ResidentRow], *, estate_id: int, state: ExistingState
) -> ResidentPlan:
    """Decide which resident memberships to create (pure)."""
    plan = ResidentPlan()
    for row in rows:
        email = row.email.strip().lower()
        user_id = state.user_ids.get(email)
        unit_id = state.unit_ids.get(row.unit_no)
        problems: list[str] = []

        if unit_id is None:
            problems.append(
                f"{email}: unit '{row.unit_no}' was not found in estate #{estate_id}"
            )
        if user_id is None:
            problems.append(
                f"{email}: no registered user with this email. Residents register "
                "themselves first; this script only links them to a unit"
            )
        if problems:
            plan.errors.extend(problems)
            continue

        declared = (state.user_declared_unit_no.get(email) or "").strip()
        if declared and declared != row.unit_no:
            plan.warnings.append(
                f"{email}: the account declared unit '{declared}' but is being linked "
                f"to '{row.unit_no}'. Confirm this with the resident."
            )
        if (user_id, unit_id) in state.membership_units:
            plan.skips.append(f"{email} is already linked to {row.unit_no}")
            continue
        others = [unit for unit in state.linked_units(user_id) if unit != unit_id]
        if others:
            plan.warnings.append(
                f"{email}: already linked to another unit in this estate "
                f"(property ids {others}); adding '{row.unit_no}' as well."
            )

        plan.links.append(
            MembershipSpec(
                email=email,
                role=UserRole.resident.value,
                unit_no=row.unit_no,
                user_id=user_id,
                property_id=unit_id,
            )
        )
    return plan


# --------------------------------------------------------------------------- #
# applying (the only code that writes)
# --------------------------------------------------------------------------- #


@dataclass
class ApplyResult:
    estate_id: int | None = None
    units_created: int = 0
    users_created: int = 0
    providers_created: int = 0
    memberships_created: int = 0
    credentials: list[tuple[str, str, str]] = field(default_factory=list)


async def apply_estate_plan(
    session: AsyncSession,
    spec: EstateSpec,
    plan: ProvisionPlan,
    *,
    known_user_ids: dict[str, int] | None = None,
) -> ApplyResult:
    """Write the plan. One commit for the whole use case."""
    result = ApplyResult()
    known = dict(known_user_ids or {})

    if plan.create_estate:
        estate = Estate(
            name=spec.name,
            suburb=spec.suburb,
            city=spec.city,
            province=spec.province,
            description=spec.description,
            # A real pilot estate is never demo data.
            is_demo=False,
        )
        session.add(estate)
        await session.flush()
        if estate.estate_id is None:
            raise ProvisionError("The database did not assign an estate id.")
        estate_id = estate.estate_id
    else:
        # Adding units or people to an estate that is already provisioned.
        found = await session.execute(select(Estate).where(Estate.name == spec.name))
        estate = found.scalar_one_or_none()
        if estate is None:
            raise ProvisionError(
                f"Estate '{spec.name}' vanished between the plan and the write. Stop."
            )
        estate_id = estate.estate_id
    result.estate_id = estate_id

    for unit in plan.units:
        session.add(
            Property(
                estate_id=estate_id,
                unit_no=unit.unit_no,
                complex_name=unit.complex_name,
                street_address=unit.street_address,
                suburb=unit.suburb,
                size_m2=unit.size_m2,
                bedrooms=unit.bedrooms,
                bathrooms=unit.bathrooms,
            )
        )
        result.units_created += 1
    await session.flush()

    created_users: dict[str, User] = {}
    to_create: list[tuple[PersonSpec, str]] = [
        *((admin, UserRole.hoa_admin.value) for admin in plan.admins),
        *(
            (person, UserRole.service_provider.value)
            for person, _provider in plan.providers
        ),
    ]
    for person, role in to_create:
        password = generate_password()
        user = User(
            email=person.email,
            full_name=person.full_name,
            password_hash=hash_password(password),
            role=role,
            hoa_approved=True,
            email_verified=True,
        )
        session.add(user)
        created_users[person.email] = user
        result.credentials.append((person.email, role, password))
    await session.flush()
    result.users_created = len(created_users)

    for person, provider_spec in plan.providers:
        session.add(
            ServiceProvider(
                user_id=created_users[person.email].user_id,
                full_name=provider_spec.full_name,
                trade=provider_spec.trade,
                phone=provider_spec.phone,
                email=provider_spec.email,
                verified=True,
                emergency_available=provider_spec.emergency_available,
                total_reviews=0,
            )
        )
        result.providers_created += 1
    await session.flush()

    for membership in plan.memberships:
        user_id = membership.user_id
        if user_id is None:
            created = created_users.get(membership.email)
            user_id = created.user_id if created is not None else known.get(membership.email)
        if user_id is None:
            raise ProvisionError(
                f"Cannot create the membership for {membership.email}: no user id."
            )
        session.add(
            EstateMembership(
                user_id=user_id,
                estate_id=estate_id,
                property_id=membership.property_id,
                membership_role=membership.role,
            )
        )
        result.memberships_created += 1
    await session.flush()

    await session.commit()
    return result


async def apply_resident_plan(
    session: AsyncSession, *, estate_id: int, plan: ResidentPlan
) -> int:
    """Create the planned resident memberships. One commit for the whole use case."""
    for link in plan.links:
        session.add(
            EstateMembership(
                user_id=link.user_id,
                estate_id=estate_id,
                property_id=link.property_id,
                membership_role=link.role,
            )
        )
    if plan.links:
        await session.flush()
        await session.commit()
    return len(plan.links)


# --------------------------------------------------------------------------- #
# output
# --------------------------------------------------------------------------- #


def print_target(url: str) -> None:
    print(f"Target database: {redact_database_url(url)}")
    print("(credentials come from DATABASE_URL and are not shown)")


def print_plan(spec: EstateSpec, plan: ProvisionPlan) -> None:
    print(
        f"Estate to create: {spec.name} (is_demo=false)"
        if plan.create_estate
        else f"Estate already exists: {spec.name}"
    )
    if plan.units:
        print(
            f"Units to create ({len(plan.units)}): "
            + ", ".join(unit.unit_no for unit in plan.units)
        )
    if plan.admins:
        print(
            f"HOA admins to create ({len(plan.admins)}): "
            + ", ".join(admin.email for admin in plan.admins)
        )
    if plan.providers:
        print(
            f"Service providers to create ({len(plan.providers)}): "
            + ", ".join(f"{person.email} ({p.trade})" for person, p in plan.providers)
        )
    if plan.memberships:
        print(
            "Memberships to create: "
            + ", ".join(f"{m.email} -> {m.role}" for m in plan.memberships)
        )
    for skip in plan.skips:
        print(f"skip: {skip}")
    for warning in plan.warnings:
        print(f"WARNING: {warning}")
    if not plan.creates_anything():
        print("Nothing to do: the estate and everything in it already exist.")


def print_credentials(credentials: Iterable[tuple[str, str, str]]) -> None:
    rows = list(credentials)
    if not rows:
        return
    print("")
    print("Passwords for the accounts created just now - shown ONCE, store them now:")
    for email, role, password in rows:
        print(f"  {email}  [{role}]  {password}")
    print("They are not stored anywhere in plain text and cannot be shown again.")


def print_resident_plan(plan: ResidentPlan, *, applied: bool) -> None:
    verb = "linked" if applied else "to link"
    for link in plan.links:
        print(f"resident {verb}: {link.email} -> unit {link.unit_no}")
    for skip in plan.skips:
        print(f"skip: {skip}")
    for warning in plan.warnings:
        print(f"WARNING: {warning}")
    for error in plan.errors:
        print(f"ERROR: {error}")
    if not (plan.links or plan.skips or plan.errors):
        print("Nothing to do.")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def default_session_factory():
    """A session factory bound to the URL this run has already printed."""

    @asynccontextmanager
    async def _factory():
        engine = create_async_engine(target_database_url(), echo=False)
        try:
            maker = async_sessionmaker(
                bind=engine, class_=AsyncSession, expire_on_commit=False
            )
            async with maker() as session:
                yield session
        finally:
            await engine.dispose()

    return _factory


def _guard_target(url: str, args: argparse.Namespace) -> None:
    """Refuse the obvious ways to provision into the wrong database."""
    if args.expect_database and database_name(url) != args.expect_database:
        raise ProvisionError(
            f"--expect-database {args.expect_database} does not match the target "
            f"'{database_name(url)}'. Nothing was written."
        )
    if args.apply and looks_like_a_demo_database(url) and not args.allow_demo_database:
        raise ProvisionError(
            f"The target database '{database_name(url)}' looks like a demo database, "
            "and the pilot must use its own. Pass --allow-demo-database only if you "
            "are certain. Nothing was written."
        )


async def _run_estate(args: argparse.Namespace, session_factory: Callable) -> int:
    spec = load_estate_spec(args.file)
    async with session_factory() as session:
        state = await load_estate_state(session, estate_name=spec.name)
        plan = plan_estate(spec, state)
        print_plan(spec, plan)
        if not plan.creates_anything():
            return 0
        if not args.apply:
            print("")
            print("[dry-run] no changes were written. Re-run with --apply to write.")
            return 0
        result = await apply_estate_plan(
            session, spec, plan, known_user_ids=state.user_ids
        )
        print("")
        print(
            f"Applied: estate #{result.estate_id}, {result.units_created} units, "
            f"{result.users_created} users, {result.providers_created} provider "
            f"profiles, {result.memberships_created} memberships."
        )
        print_credentials(result.credentials)
        return 0


def _resident_rows_from_args(args: argparse.Namespace) -> list[ResidentRow]:
    if args.command == "link-resident":
        return [
            ResidentRow(email=args.email.strip().lower(), unit_no=args.unit_no.strip())
        ]
    return load_residents_csv(args.file)


async def _run_residents(args: argparse.Namespace, session_factory: Callable) -> int:
    rows = _resident_rows_from_args(args)
    async with session_factory() as session:
        state = await load_unit_state(session, estate_id=args.estate_id)
        plan = plan_residents(rows, estate_id=args.estate_id, state=state)
        if not args.apply:
            print_resident_plan(plan, applied=False)
            print("")
            print("[dry-run] no changes were written. Re-run with --apply to write.")
            return 1 if plan.errors else 0
        created = await apply_resident_plan(session, estate_id=args.estate_id, plan=plan)
        print_resident_plan(plan, applied=True)
        print("")
        print(f"Applied: {created} resident memberships created.")
        return 1 if plan.errors else 0


def _add_common_flags(parser: argparse.ArgumentParser) -> None:
    """The safety switches, accepted before or after the subcommand.

    ``SUPPRESS`` defaults mean whichever copy the operator uses wins, and the
    other one does not overwrite it with a default.
    """
    parser.add_argument(
        "--apply",
        action="store_true",
        default=argparse.SUPPRESS,
        help="write the changes (without it, this is a dry run)",
    )
    parser.add_argument(
        "--expect-database",
        default=argparse.SUPPRESS,
        help="refuse to run unless the target database has this exact name",
    )
    parser.add_argument(
        "--allow-demo-database",
        action="store_true",
        default=argparse.SUPPRESS,
        help="permit writing into a database whose name looks like a demo database",
    )


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    _add_common_flags(common)

    parser = argparse.ArgumentParser(
        description="Provision a real pilot estate. Dry-run unless --apply is given."
    )
    _add_common_flags(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    estate = subparsers.add_parser(
        "estate", help="create an estate from a JSON file", parents=[common]
    )
    estate.add_argument("--file", required=True, help="estate JSON file")

    link = subparsers.add_parser(
        "link-resident", help="link one resident to a unit", parents=[common]
    )
    link.add_argument("--estate-id", type=int, required=True)
    link.add_argument("--email", required=True)
    link.add_argument("--unit-no", required=True)

    csv_parser = subparsers.add_parser(
        "link-residents-csv",
        help="link residents from a CSV (columns email,unit_no)",
        parents=[common],
    )
    csv_parser.add_argument("--estate-id", type=int, required=True)
    csv_parser.add_argument("--file", required=True)

    return parser


def _normalise_switches(args: argparse.Namespace) -> argparse.Namespace:
    """Give the suppressed switches their defaults."""
    for name, fallback in (
        ("apply", False),
        ("expect_database", None),
        ("allow_demo_database", False),
    ):
        setattr(args, name, getattr(args, name, fallback))
    return args


async def main(
    argv: Sequence[str] | None = None, *, session_factory: Callable | None = None
) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = build_parser()
    args = _normalise_switches(
        parser.parse_args(list(argv) if argv is not None else None)
    )

    try:
        url = target_database_url()
        print_target(url)
        _guard_target(url, args)
        factory = session_factory or default_session_factory()
        if args.command == "estate":
            return await _run_estate(args, factory)
        return await _run_residents(args, factory)
    except ProvisionError as exc:
        print(f"ERROR: {exc}")
        return 1


def cli() -> int:
    return asyncio.run(main())


if __name__ == "__main__":
    raise SystemExit(cli())
