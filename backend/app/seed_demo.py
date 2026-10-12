"""The demonstration estate: a guarded, deterministic, idempotent seeder.

One South African estate, with enough real operational history that every screen
and the deterministic Living Score engine have something true to work from: one
HOA administrator, twenty residents, two linked service providers, twenty-four
units, three months of complaints across the whole lifecycle (each with the events
its transitions imply), work orders, resident ratings, security incidents,
announcements and placeholder photographs.

Four rules this module keeps, because a demo that lies is worse than no demo:

* **Guarded.** It refuses to run unless the operator names the database
  (``--expect-database``) *and* the connected database's name contains "demo". A
  demo estate must never appear in a pilot or production database, and the guard
  is checked against the live connection (``SELECT current_database()``), not
  against a string in the environment.
* **Deterministic.** No randomness anywhere: the same run always produces the same
  estate, units, people, complaints, work orders and captions. All timestamps are
  offsets from one clock reading taken at the start of the run.
* **Idempotent.** If the demo estate already exists it reports so and changes
  nothing — no second estate, no second set of accounts, no extra photos.
* **Never faked AI.** No ``ai_insights`` and no ``complaint_ai_suggestions`` rows
  are ever written here. The AI layer's own tests own that data; a seeded
  "AI output" would be a claim nobody could trace back to a model.

Photographs are generated with Pillow and pushed through the **real** photo
pipeline (:class:`~app.property.services.estate_photo_service.EstatePhotoService`),
so what lands on disk is re-encoded, EXIF-free and named from a random public id.
Living Score snapshots are produced by the **real** engine
(:class:`~app.analytics.services.estate_living_score_service.LivingScoreService`)
at several past ``as_of`` dates. No score is ever inserted by hand.

Run::

    python -m app.cli seed-demo --expect-database valora_demo
"""
from __future__ import annotations

import io
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ComplaintStatus, UserRole, WorkOrderStatus
from app.community.models.announcement import Announcement
from app.community.models.complaint import Complaint
from app.community.models.complaint_event import ComplaintEvent
from app.community.models.maintenance_work_order import MaintenanceworkOrder
from app.community.models.security_incident import SecurityIncident
from app.core.security import hash_password
from app.identity.models.estate_membership import EstateMembership
from app.identity.models.user import User
from app.property.models.estate import Estate
from app.property.models.property import Property
from app.providers.models.review import Review
from app.providers.models.service_provider import ServiceProvider

DEMO_ESTATE_NAME = "Highveld Ridge Estate"
#: A local-only fixture. Override with ``VALORA_SEED_PASSWORD``; never used
#: anywhere except a database the guard below has already accepted.
DEFAULT_DEMO_PASSWORD = "ValoraDemo123!"
DEMO_EMAIL_DOMAIN = "example.com"

DEMO_UNIT_COUNT = 24
DEMO_RESIDENT_COUNT = 20
#: How far back the estate is backdated. The brief's floor is 60 days; 120 gives
#: the engine's rolling 90-day window a full history to score.
DEMO_HISTORY_DAYS = 120
DEMO_COMPLAINT_COUNT = 36
DEMO_PHOTO_COUNT = 5
#: Real Living Score snapshots, oldest first, as days before "now".
DEMO_SCORE_AS_OF_OFFSETS: tuple[int, ...] = (84, 56, 28, 0)


class SeedGuardError(RuntimeError):
    """The seed was pointed at a database it must never write to."""


# --------------------------------------------------------------------------- #
# Guards
# --------------------------------------------------------------------------- #
async def current_database_name(db: AsyncSession) -> str:
    """The name of the database this session is actually connected to."""
    result = await db.execute(text("SELECT current_database()"))
    return str(result.scalar_one())


def validate_seed_target(database_name: str, *, expect_database: str) -> None:
    """Refuse anything but the named, demo-looking database. Nothing is written.

    Pure, so it is unit-testable without a database.
    """
    if database_name != expect_database:
        raise SeedGuardError(
            f"--expect-database {expect_database!r} does not match the connected "
            f"database {database_name!r}. Nothing was seeded."
        )
    if "demo" not in database_name.lower():
        raise SeedGuardError(
            f"The connected database {database_name!r} is not a demo database "
            "(its name must contain 'demo'). Nothing was seeded."
        )


def _demo_password() -> str:
    return os.getenv("VALORA_SEED_PASSWORD") or DEFAULT_DEMO_PASSWORD


# --------------------------------------------------------------------------- #
# Fixed content
# --------------------------------------------------------------------------- #
_RESIDENT_FIRST_NAMES: tuple[str, ...] = (
    "Thandi", "Sipho", "Lerato", "Pieter", "Aisha", "Johan", "Nomvula", "Kabelo",
    "Maria", "Tebogo", "Annelie", "Musa", "Zanele", "Riaan", "Precious",
    "Bongani", "Elmarie", "Tshepo", "Ntombi", "Andries",
)
_RESIDENT_LAST_NAMES: tuple[str, ...] = (
    "Nkosi", "Mokoena", "Dlamini", "van Wyk", "Patel", "Botha", "Molefe",
    "Sithole", "Naidoo", "Khumalo", "Fourie", "Ndlovu", "Mahlangu", "Pretorius",
    "Cele", "Zwane", "Mabaso", "Ndlangamandla", "September", "Grobbelaar",
)

_UNIT_SIZES: tuple[Decimal, ...] = (
    Decimal("142.00"), Decimal("118.00"), Decimal("96.00"),
    Decimal("168.00"), Decimal("132.00"), Decimal("104.00"),
)
_UNIT_BEDROOMS: tuple[int, ...] = (3, 3, 2, 4, 3, 2)
_UNIT_BATHROOMS: tuple[int, ...] = (2, 2, 1, 3, 2, 2)

#: (category, priority, description). Categories are the published vocabulary.
_COMPLAINT_TEMPLATES: tuple[tuple[str, str, str], ...] = (
    ("water", "urgent", "Burst pipe flooding the ground-floor guest bathroom."),
    ("security", "high", "Perimeter gate at the north boom fails to close after 22:00."),
    ("electrical", "normal", "Streetlight outside the unit has been dark for four nights."),
    ("infrastructure", "high", "Stormwater drain in the shared driveway backs up in heavy rain."),
    ("waste", "normal", "Refuse collection has missed the east row for two weeks."),
    ("parking", "low", "Visitor bay has been occupied by the same trailer for a month."),
    ("noise", "normal", "Construction noise outside the permitted hours on two weekends."),
    ("gardens", "low", "Communal irrigation is spraying onto the paving and the wall."),
    ("administrative", "low", "Levy statement has not been received for two months."),
    ("water", "high", "Low water pressure in the upstairs bathrooms since the mains work."),
    ("electrical", "urgent", "Distribution board trips whenever the pool pump starts."),
    ("security", "urgent", "Two attempted break-ins reported on the east boundary wall."),
    ("infrastructure", "normal", "Pothole forming at the entrance to the complex."),
    ("other", "low", "Complex signage at the main gate is illegible at night."),
)

_COMPLETION_NOTES: tuple[str, ...] = (
    "Replaced the failed section of pipe and pressure-tested the line.",
    "Fitted a new gate motor and re-aligned the boom.",
    "Replaced the fitting and checked the rest of the circuit.",
    "Cleared the drain and re-graded the channel.",
    "Repaired the irrigation line and re-set the timer.",
    "Serviced the distribution board and replaced two breakers.",
)
#: (category, severity, status, occurred_days_ago) — resolved ones carry a
#: resolution time, because the database check constraint pairs the two.
_INCIDENTS: tuple[tuple[str, str, str, int], ...] = (
    ("suspicious_activity", "low", "resolved", 84),
    ("vandalism", "medium", "resolved", 68),
    ("access_control_failure", "high", "resolved", 52),
    ("theft", "high", "resolved", 39),
    ("trespass", "medium", "investigating", 26),
    ("perimeter_breach", "critical", "open", 14),
)

#: (title, message, created_days_ago)
_ANNOUNCEMENTS: tuple[tuple[str, str, int], ...] = (
    (
        "Scheduled water interruption — Tuesday 09:00 to 13:00",
        "The municipality is replacing a valve on Ridge Close. Please store drinking "
        "water for the morning and avoid running appliances.",
        61,
    ),
    (
        "Annual general meeting",
        "The AGM will review security spend, the maintenance backlog and the estate's "
        "Living Score. Quorum is required to approve the budget.",
        33,
    ),
    (
        "North gate camera upgrade completed",
        "All four north boundary cameras were replaced this week. Please report any "
        "blind spots through the complaints portal.",
        18,
    ),
    (
        "Bulk refuse day moves to Wednesday",
        "From next week the municipal collection moves one day later. Please put bins "
        "out on Tuesday evening.",
        9,
    ),
    (
        "Boil-water notice lifted",
        "The laboratory has cleared the sample taken after the mains repair. Tap water "
        "is safe to drink again.",
        2,
    ),
)

_PHOTO_CAPTIONS: tuple[str, ...] = (
    "Placeholder photograph — the main gate from Inside Crescent.",
    "Placeholder photograph — the communal lawn and braai area.",
    "Placeholder photograph — a typical unit frontage.",
    "Placeholder photograph — the north boundary wall and camera mast.",
    "Placeholder photograph — the clubhouse and visitors' parking.",
)
_PHOTO_COLOURS: tuple[tuple[int, int, int], ...] = (
    (86, 112, 94), (132, 118, 92), (104, 96, 120), (120, 108, 96), (92, 116, 128),
)


# --------------------------------------------------------------------------- #
# Building blocks
# --------------------------------------------------------------------------- #
def _anchor() -> datetime:
    """One clock reading for the whole run; every timestamp derives from it."""
    return datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)


def _ago(anchor: datetime, days: float, *, hours: float = 0.0) -> datetime:
    return anchor - timedelta(days=days, hours=hours)


def placeholder_jpeg(index: int) -> bytes:
    """A deterministic placeholder photograph, as JPEG bytes.

    Drawn rather than fetched, so the seeder needs no network and no bundled
    binary: an unmistakably synthetic ''picture'' of a complex — sky, ground, a
    few blocks and a label that says it is a placeholder.
    """
    from PIL import Image, ImageDraw

    colour = _PHOTO_COLOURS[index % len(_PHOTO_COLOURS)]
    width, height = 1600, 1000
    image = Image.new("RGB", (width, height), (222, 228, 232))
    draw = ImageDraw.Draw(image)

    horizon = int(height * 0.62)
    draw.rectangle((0, 0, width, horizon), fill=(196, 214, 226))
    draw.rectangle((0, horizon, width, height), fill=(118, 134, 108))
    draw.ellipse((width - 320, 90, width - 140, 270), fill=(238, 222, 176))

    block_top = horizon - 260
    for column in range(4):
        left = 140 + column * 340
        draw.rectangle((left, block_top, left + 250, horizon), fill=colour)
        for row in range(3):
            for cell in range(2):
                window_left = left + 40 + cell * 110
                window_top = block_top + 30 + row * 80
                draw.rectangle(
                    (window_left, window_top, window_left + 70, window_top + 50),
                    fill=(242, 240, 232),
                )
    draw.rectangle((0, horizon - 12, width, horizon + 12), fill=(96, 96, 96))

    label = f"VALORA demo placeholder photograph {index + 1} of {DEMO_PHOTO_COUNT}"
    draw.rectangle((40, height - 120, 40 + 24 * len(label) // 2, height - 50), fill=(28, 32, 36))
    draw.text((60, height - 105), label, fill=(240, 240, 236))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()


def demo_user_specs() -> tuple[tuple[str, str, str], ...]:
    """``(email, full_name, role)`` for every demo sign-in, in print order.

    One source of truth: the seeder creates these accounts and the CLI prints
    this table, so the credentials an operator reads are the accounts that exist.
    """
    specs = [(f"admin@{DEMO_EMAIL_DOMAIN}", "Nomsa Mokoena", UserRole.hoa_admin.value)]
    for index in range(DEMO_RESIDENT_COUNT):
        specs.append(
            (
                f"resident{index + 1:02d}@{DEMO_EMAIL_DOMAIN}",
                f"{_RESIDENT_FIRST_NAMES[index]} {_RESIDENT_LAST_NAMES[index]}",
                UserRole.resident.value,
            )
        )
    specs.append((f"provider01@{DEMO_EMAIL_DOMAIN}", "Sipho Dlamini", UserRole.service_provider.value))
    specs.append((f"provider02@{DEMO_EMAIL_DOMAIN}", "Marius Botha", UserRole.service_provider.value))
    specs.append((f"investor@{DEMO_EMAIL_DOMAIN}", "James van Wyk", UserRole.investor.value))
    return tuple(specs)


def demo_accounts() -> list[dict[str, str]]:
    """The demo sign-in table, as the CLI prints it. Never a password value."""
    return [
        {"role": role, "email": email, "full_name": full_name}
        for email, full_name, role in demo_user_specs()
    ]


def _new_user(*, email: str, full_name: str, role: str, password_hash: str) -> User:
    return User(
        full_name=full_name,
        email=email,
        password_hash=password_hash,
        role=role,
        hoa_approved=True,
        email_verified=True,
    )


# --------------------------------------------------------------------------- #
# The seed
# --------------------------------------------------------------------------- #
async def seed_demo(
    db: AsyncSession,
    *,
    expect_database: str,
    upload_dir: str | Path | None = None,
) -> dict[str, object]:
    """Create the demo world. Returns a summary of what happened.

    Refuses before writing anything unless the live database is the one named by
    ``expect_database`` and its name contains "demo".
    """
    target = await current_database_name(db)
    validate_seed_target(target, expect_database=expect_database)

    existing = await db.execute(select(Estate).where(Estate.name == DEMO_ESTATE_NAME))
    found = existing.scalar_one_or_none()
    if found is not None:
        return {
            "created": False,
            "estate": DEMO_ESTATE_NAME,
            "estate_id": found.estate_id,
            "database": target,
            "users": demo_accounts(),
            "message": (
                f"{DEMO_ESTATE_NAME} already exists in {target} — nothing changed."
            ),
        }

    anchor = _anchor()
    password_hash = hash_password(_demo_password())

    # ---------------------------------------------------------------- estate #
    estate = Estate(
        name=DEMO_ESTATE_NAME,
        suburb="Centurion",
        city="Tshwane",
        province="Gauteng",
        description=(
            "A 24-unit private security estate in Centurion, operated by a volunteer "
            "HOA committee. Demonstration data: the history below was generated, not "
            "collected from a real community."
        ),
        # Seeded demonstration data: never treated as a real customer's estate.
        is_demo=True,
        # Published, and opted in to showing its score, so the demonstration covers
        # the public directory as well as the signed-in app.
        is_public=True,
        show_living_score=True,
        created_at=_ago(anchor, DEMO_HISTORY_DAYS),
    )
    db.add(estate)
    await db.flush()

    # ----------------------------------------------------------------- users #
    by_email: dict[str, User] = {}
    for email, full_name, role in demo_user_specs():
        by_email[email] = _new_user(
            email=email, full_name=full_name, role=role, password_hash=password_hash
        )
    db.add_all(list(by_email.values()))
    await db.flush()

    admin = by_email[f"admin@{DEMO_EMAIL_DOMAIN}"]
    investor = by_email[f"investor@{DEMO_EMAIL_DOMAIN}"]
    residents: list[User] = [
        by_email[f"resident{index + 1:02d}@{DEMO_EMAIL_DOMAIN}"]
        for index in range(DEMO_RESIDENT_COUNT)
    ]
    provider_users: list[User] = [
        by_email[f"provider{index:02d}@{DEMO_EMAIL_DOMAIN}"] for index in (1, 2)
    ]

    # ----------------------------------------------------------------- units #
    units: list[Property] = []
    for number in range(1, DEMO_UNIT_COUNT + 1):
        shape = (number - 1) % len(_UNIT_SIZES)
        units.append(
            Property(
                estate_id=estate.estate_id,
                unit_no=f"HR-{number:02d}",
                complex_name="Highveld Ridge",
                street_address=f"{number} Ridge Close",
                suburb="Centurion",
                size_m2=_UNIT_SIZES[shape],
                bedrooms=_UNIT_BEDROOMS[shape],
                bathrooms=_UNIT_BATHROOMS[shape],
            )
        )
    db.add_all(units)
    await db.flush()

    # ----------------------------------------------------------- memberships #
    db.add_all(
        [
            EstateMembership(
                user_id=admin.user_id,
                estate_id=estate.estate_id,
                property_id=None,
                membership_role=UserRole.hoa_admin.value,
            ),
            EstateMembership(
                user_id=investor.user_id,
                estate_id=estate.estate_id,
                property_id=None,
                membership_role=UserRole.investor.value,
            ),
            # ADR-007: one resident may hold more than one unit in the same estate.
            # resident01 owns two units, which keeps that rule visible in the demo.
            EstateMembership(
                user_id=residents[0].user_id,
                estate_id=estate.estate_id,
                property_id=units[0].unit_id,
                membership_role=UserRole.resident.value,
            ),
            EstateMembership(
                user_id=residents[0].user_id,
                estate_id=estate.estate_id,
                property_id=units[3].unit_id,
                membership_role=UserRole.resident.value,
            ),
        ]
    )
    # Who lives where, so complaints are filed against an occupied unit.
    occupancies: list[tuple[User, Property]] = [
        (residents[0], units[0]),
        (residents[0], units[3]),
    ]
    # resident02..resident20 take one unit each, skipping unit 4 (already held).
    unit_cursor = 1
    for resident in residents[1:]:
        if unit_cursor == 3:  # units[3] belongs to resident01
            unit_cursor += 1
        unit = units[unit_cursor]
        resident.unit_no = unit.unit_no
        db.add(
            EstateMembership(
                user_id=resident.user_id,
                estate_id=estate.estate_id,
                property_id=unit.unit_id,
                membership_role=UserRole.resident.value,
            )
        )
        occupancies.append((resident, unit))
        unit_cursor += 1
    residents[0].unit_no = units[0].unit_no
    for provider_user in provider_users:
        db.add(
            EstateMembership(
                user_id=provider_user.user_id,
                estate_id=estate.estate_id,
                property_id=None,
                membership_role=UserRole.service_provider.value,
            )
        )

    # -------------------------------------------------------- service providers #
    providers = [
        ServiceProvider(
            user_id=provider_users[0].user_id,
            full_name="Sipho Dlamini",
            trade="plumbing",
            phone="0821110001",
            email=f"provider01@{DEMO_EMAIL_DOMAIN}",
            verified=True,
            emergency_available=True,
            total_reviews=0,
        ),
        ServiceProvider(
            user_id=provider_users[1].user_id,
            full_name="Marius Botha",
            trade="electrical",
            phone="0821110002",
            email=f"provider02@{DEMO_EMAIL_DOMAIN}",
            verified=True,
            emergency_available=False,
            total_reviews=0,
        ),
    ]
    db.add_all(providers)
    await db.flush()

    # ------------------------------------------------------------- complaints #
    complaints: list[Complaint] = []
    for index in range(DEMO_COMPLAINT_COUNT):
        category, priority, description = _COMPLAINT_TEMPLATES[
            index % len(_COMPLAINT_TEMPLATES)
        ]
        # Oldest first: 36 complaints spread over 108 days (~3 days apart), so the
        # newest are still open and the oldest are long closed.
        created_ago = 108 - index * 3
        created = _ago(anchor, created_ago)
        reviewed = created + timedelta(hours=9)
        assigned = reviewed + timedelta(hours=14)
        started = assigned + timedelta(hours=20)
        resolved = started + timedelta(days=2, hours=6)

        if index < 20:
            status = (
                ComplaintStatus.rated.value
                if index % 3 == 1
                else ComplaintStatus.resolved.value
            )
        elif index < 24:
            status = ComplaintStatus.in_progress.value
        elif index < 28:
            status = ComplaintStatus.assigned.value
        elif index < 32:
            status = ComplaintStatus.reviewed.value
        else:
            status = ComplaintStatus.submitted.value

        complainant, unit = occupancies[index % len(occupancies)]
        complaint = Complaint(
            user_id=complainant.user_id,
            estate_id=estate.estate_id,
            unit_id=unit.unit_id,
            category=category,
            description=description,
            priority=priority,
            is_anonymous=False,
            status=status,
            created_at=created,
            reviewed_at=None if status == ComplaintStatus.submitted.value else reviewed,
            assigned_at=(
                assigned
                if status
                in {
                    ComplaintStatus.assigned.value,
                    ComplaintStatus.in_progress.value,
                    ComplaintStatus.resolved.value,
                    ComplaintStatus.rated.value,
                }
                else None
            ),
            started_at=(
                started
                if status
                in {
                    ComplaintStatus.in_progress.value,
                    ComplaintStatus.resolved.value,
                    ComplaintStatus.rated.value,
                }
                else None
            ),
            resolved_at=(
                resolved
                if status
                in {ComplaintStatus.resolved.value, ComplaintStatus.rated.value}
                else None
            ),
        )
        db.add(complaint)
        complaints.append(complaint)
    await db.flush()

    # The event log for every transition the status implies, in order, with the
    # same timestamps as the complaint's own columns.
    for complaint in complaints:
        db.add(
            ComplaintEvent(
                complaint_id=complaint.complaint_id,
                estate_id=estate.estate_id,
                actor_user_id=complaint.user_id,
                event_type="submitted",
                to_status=ComplaintStatus.submitted.value,
                occurred_at=complaint.created_at,
            )
        )
        transitions = (
            ("reviewed", ComplaintStatus.submitted.value, ComplaintStatus.reviewed.value, complaint.reviewed_at, admin.user_id),
            ("assigned", ComplaintStatus.reviewed.value, ComplaintStatus.assigned.value, complaint.assigned_at, admin.user_id),
            ("in_progress", ComplaintStatus.assigned.value, ComplaintStatus.in_progress.value, complaint.started_at, admin.user_id),
            ("resolved", ComplaintStatus.in_progress.value, ComplaintStatus.resolved.value, complaint.resolved_at, admin.user_id),
            ("rated", ComplaintStatus.resolved.value, ComplaintStatus.rated.value, complaint.resolved_at, complaint.user_id),
        )
        for event_type, from_status, to_status, occurred_at, actor in transitions:
            if occurred_at is None:
                continue
            if event_type == "rated" and complaint.status != ComplaintStatus.rated.value:
                continue
            db.add(
                ComplaintEvent(
                    complaint_id=complaint.complaint_id,
                    estate_id=estate.estate_id,
                    actor_user_id=actor,
                    event_type=event_type,
                    from_status=from_status,
                    to_status=to_status,
                    occurred_at=occurred_at,
                    note=(
                        "Progressed by the HOA during the daily review."
                        if event_type not in {"rated", "resolved"}
                        else None
                    ),
                )
            )

    # ------------------------------------------------------------ work orders #
    work_orders: list[MaintenanceworkOrder] = []
    for index, complaint in enumerate(complaints):
        if complaint.status in {
            ComplaintStatus.submitted.value,
            ComplaintStatus.reviewed.value,
        }:
            continue
        provider = providers[index % len(providers)]
        completed = complaint.status in {
            ComplaintStatus.resolved.value,
            ComplaintStatus.rated.value,
        }
        assigned_at = complaint.assigned_at or complaint.created_at
        # A rated complaint carries the resident's own rating on its completed
        # work order. Five of those ratings fall inside the engine's 90-day
        # window, which is what makes the satisfaction component measurable.
        rating = (
            (3 + (index // 3) % 3)
            if complaint.status == ComplaintStatus.rated.value
            else None
        )
        work_orders.append(
            MaintenanceworkOrder(
                complaint_id=complaint.complaint_id,
                estate_id=estate.estate_id,
                provider_id=provider.provider_id,
                status=(
                    WorkOrderStatus.completed.value
                    if completed
                    else (
                        WorkOrderStatus.in_progress.value
                        if complaint.status == ComplaintStatus.in_progress.value
                        else WorkOrderStatus.assigned.value
                    )
                ),
                job_cost=Decimal(750 + (index % 7) * 320) + Decimal("0.50"),
                resident_rating=rating,
                completion_notes=(
                    _COMPLETION_NOTES[index % len(_COMPLETION_NOTES)] if completed else None
                ),
                assigned_at=assigned_at,
                resolved_at=complaint.resolved_at,
                actual_completion_date=complaint.resolved_at,
                estimated_completion_date=assigned_at + timedelta(days=3),
            )
        )
    db.add_all(work_orders)

    # ------------------------------------------------------ provider reviews #
    review_specs = (
        (providers[0], 5, "Arrived within the hour and left the site spotless."),
        (providers[0], 5, "Second call-out for the same leak, fixed properly this time."),
        (providers[0], 4, "Good work; the invoice took a while to arrive."),
        (providers[1], 4, "Sorted the gate motor the same day."),
        (providers[1], 3, "Tidy work but the gate still sticks occasionally."),
    )
    ratings_by_provider: dict[int, list[int]] = {}
    for offset, (provider, rating, comment) in enumerate(review_specs):
        db.add(
            Review(
                user_id=residents[offset % len(residents)].user_id,
                provider_id=provider.provider_id,
                rating=rating,
                comment=comment,
                created_at=_ago(anchor, 8 + offset * 5),
            )
        )
        ratings_by_provider.setdefault(provider.provider_id, []).append(rating)
    for provider in providers:
        ratings = ratings_by_provider.get(provider.provider_id, [])
        provider.total_reviews = len(ratings)
        provider.avg_rating = (
            (Decimal(sum(ratings)) / Decimal(len(ratings))).quantize(Decimal("0.01"))
            if ratings
            else None
        )

    # ------------------------------------------------------ security incidents #
    for index, (category, severity, status, days_ago) in enumerate(_INCIDENTS):
        occurred_at = _ago(anchor, days_ago, hours=4)
        resolved_at = (
            occurred_at + timedelta(days=2 + index) if status == "resolved" else None
        )
        db.add(
            SecurityIncident(
                estate_id=estate.estate_id,
                property_id=None if index % 3 else units[index].unit_id,
                category=category,
                severity=severity,
                status=status,
                occurred_at=occurred_at,
                resolved_at=resolved_at,
                resolution_notes=(
                    "Patrol route changed and the gate contractor re-programmed the "
                    "controllers."
                    if resolved_at is not None
                    else None
                ),
                created_by=admin.user_id,
            )
        )

    # ----------------------------------------------------------- announcements #
    db.add_all(
        [
            Announcement(
                estate_id=estate.estate_id,
                title=title,
                message=message,
                created_by=admin.user_id,
                created_at=_ago(anchor, days_ago),
            )
            for title, message, days_ago in _ANNOUNCEMENTS
        ]
    )

    # One commit for the whole use case: estate, people, units, operations.
    await db.commit()

    # ------------------------------------------------------------ photographs #
    # Through the real pipeline, so the demo exercises the same re-encode,
    # EXIF-stripping and random-name path a real upload does.
    from app.property.services.estate_photo_service import EstatePhotoService

    photo_service = EstatePhotoService(db, upload_dir=upload_dir)
    photos = []
    for index in range(DEMO_PHOTO_COUNT):
        photos.append(
            await photo_service.upload_photo(
                admin,
                estate_id=estate.estate_id,
                filename=f"placeholder-{index + 1}.jpg",
                content_type="image/jpeg",
                data=placeholder_jpeg(index),
                caption=_PHOTO_CAPTIONS[index % len(_PHOTO_CAPTIONS)],
            )
        )

    # ---------------------------------------------------- living score history #
    # The real engine, at real past dates. Nothing is inserted by hand, so every
    # number in the demo can be traced back to stored inputs.
    from app.analytics.services.estate_living_score_service import LivingScoreService

    score_service = LivingScoreService(db)
    scores = []
    for offset in DEMO_SCORE_AS_OF_OFFSETS:
        snapshot = await score_service.calculate_and_snapshot(
            estate.estate_id, actor=None, as_of=_ago(anchor, offset)
        )
        scores.append(
            {
                "as_of": snapshot.as_of.isoformat(),
                "status": snapshot.status,
                "overall_score": (
                    None if snapshot.overall_score is None else str(snapshot.overall_score)
                ),
                "engine_version": snapshot.engine_version,
            }
        )

    return {
        "created": True,
        "estate": estate.name,
        "estate_id": estate.estate_id,
        "database": target,
        "history_days": DEMO_HISTORY_DAYS,
        "users": demo_accounts(),
        "properties": len(units),
        "residents": len(residents),
        "providers": len(providers),
        "complaints": len(complaints),
        "work_orders": len(work_orders),
        "incidents": len(_INCIDENTS),
        "announcements": len(_ANNOUNCEMENTS),
        "photos": len(photos),
        "photo_public_ids": [photo.public_id for photo in photos],
        "scores": scores,
    }


async def count_demo_ai_rows(db: AsyncSession) -> dict[str, int]:
    """How many AI rows exist for the demo estate. Always zero after a seed.

    Lives here so a test can assert the promise ("AI output is never faked")
    against the same models the AI layer writes.
    """
    from app.analytics.models.ai_insight import AIInsight
    from app.community.models.complaint_ai_suggestion import ComplaintAISuggestion

    insights = await db.execute(select(func.count()).select_from(AIInsight))
    suggestions = await db.execute(select(func.count()).select_from(ComplaintAISuggestion))
    return {"ai_insights": int(insights.scalar_one()), "ai_suggestions": int(suggestions.scalar_one())}


__all__ = [
    "DEFAULT_DEMO_PASSWORD",
    "demo_accounts",
    "demo_user_specs",
    "DEMO_EMAIL_DOMAIN",
    "DEMO_ESTATE_NAME",
    "DEMO_HISTORY_DAYS",
    "DEMO_SCORE_AS_OF_OFFSETS",
    "SeedGuardError",
    "count_demo_ai_rows",
    "current_database_name",
    "placeholder_jpeg",
    "seed_demo",
    "validate_seed_target",
]
