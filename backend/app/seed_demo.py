"""The demonstration estates: a guarded, deterministic, idempotent seeder.

Five distinct fictional South African residential complexes with contrasting management performance:
- Silverleaf Reserve (Premium, exceptionally well-managed gated estate)
- Willowbrook Mews (Middle-market townhouse complex, well-managed)
- Lakeside Gardens (Established residential estate, mixed operational performance)
- Eastbank Court (Ageing apartment block, maintenance backlogs and slow turnaround)
- Quarry View Flats (High-density complex, acute operational strain and severe backlogs)

Four core rules:
* Guarded: Refuses to run against non-development / non-demo databases.
* Deterministic: Timestamps and histories derived from one start anchor.
* Idempotent: If complexes already exist, they are preserved without duplication.
* Real Engine: Living Score snapshots are computed by the real v1.0.0 engine.
"""
from __future__ import annotations

import io
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from PIL import Image, ImageDraw
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli import snapshot_estate_living_score
from app.common.enums import ComplaintStatus, UserRole, WorkOrderStatus
from app.community.models.announcement import Announcement
from app.community.models.complaint import Complaint
from app.community.models.complaint_ai_suggestion import ComplaintAISuggestion
from app.community.models.complaint_event import ComplaintEvent
from app.community.models.maintenance_work_order import MaintenanceworkOrder
from app.community.models.security_incident import SecurityIncident
from app.core.security import hash_password
from app.identity.domain.join_code import generate_join_code
from app.identity.models.estate_join_code import EstateJoinCode
from app.identity.models.estate_membership import EstateMembership
from app.identity.models.user import User
from app.property.models.estate import Estate
from app.property.models.property import Property
from app.property.services.estate_photo_service import EstatePhotoService
from app.providers.models.review import Review
from app.providers.models.service_provider import ServiceProvider

DEFAULT_DEMO_PASSWORD = "ValoraDemo!2026"
DEMO_EMAIL_DOMAIN = "example.com"
DEMO_HISTORY_DAYS = 120
DEMO_SCORE_AS_OF_OFFSETS: tuple[int, ...] = (84, 56, 28, 0)

DEMO_ESTATE_NAMES = (
    "Silverleaf Reserve",
    "Willowbrook Mews",
    "Lakeside Gardens",
    "Eastbank Court",
    "Quarry View Flats",
)
DEMO_ESTATE_NAME = DEMO_ESTATE_NAMES[0]
DEMO_UNIT_COUNT = 24
DEMO_RESIDENT_COUNT = 20
DEMO_COMPLAINT_COUNT = 36
DEMO_PHOTO_COUNT = 5


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
    """Refuse anything but the named, demo/dev database. Nothing is written."""
    if database_name != expect_database:
        raise SeedGuardError(
            f"--expect-database {expect_database!r} does not match the connected "
            f"database {database_name!r}. Nothing was seeded."
        )
    # Refuse pilot or production
    db_lower = database_name.lower()
    if "pilot" in db_lower or "prod" in db_lower:
        raise SeedGuardError(
            f"The connected database {database_name!r} is not a demo database "
            "(its name must contain 'demo'). Nothing was seeded."
        )
    if "demo" not in db_lower and database_name not in ("valora_db", "neondb"):
        raise SeedGuardError(
            f"The connected database {database_name!r} is not a demo database "
            "(its name must contain 'demo'). Nothing was seeded."
        )


def _demo_password() -> str:
    return os.getenv("VALORA_SEED_PASSWORD") or DEFAULT_DEMO_PASSWORD


def _anchor() -> datetime:
    """One clock reading for the whole run; every timestamp derives from it."""
    return datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)


def _ago(anchor: datetime, days: float, *, hours: float = 0.0) -> datetime:
    return anchor - timedelta(days=days, hours=hours)


def placeholder_jpeg(label_text: str = "Valora Estate Photo", colour: tuple[int, int, int] = (86, 112, 94)) -> bytes:
    """A deterministic placeholder photograph, as JPEG bytes."""
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

    draw.rectangle((40, height - 120, 40 + 24 * len(label_text) // 2, height - 50), fill=(28, 32, 36))
    draw.text((60, height - 105), label_text, fill=(240, 240, 236))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()


# --------------------------------------------------------------------------- #
# Configurations for the 5 Complexes
# --------------------------------------------------------------------------- #
COMPLEX_CONFIGS = [
    {
        "key": "SR",
        "name": "Silverleaf Reserve",
        "suburb": "Constantia",
        "city": "Cape Town",
        "province": "Western Cape",
        "street": "Silverleaf Drive",
        "description": "A premier 24-unit private security estate in Constantia, featuring contemporary architecture, pristine indigenous landscaping, 24-hour manned gatehouse control, and exceptional maintenance turnaround.",
        "admin": ("hoa.silverleaf@example.com", "Nomsa Mokoena"),
        "unit_count": 24,
        "resident_count": 20,
        "unit_prefix": "SR",
        "complaint_target": 14,
        "in_window": 11,
        "resolved_target": 12,
        "avg_res_days": (1.2, 2.8),
        "wo_target": 13,
        "wo_completed": 11,
        "ratings": [5, 5, 5, 4, 5, 5, 4, 5, 5, 5, 4],
        "incidents": [
            ("access_control_failure", "low", "resolved", 45, 2),
        ],
        "announcements": [
            ("Annual General Meeting & Financial Presentation", "The AGM will review perimeter security upgrades, landscaping reserves, and the estate Living Score. Refreshments provided at the clubhouse.", 18),
            ("Fibre Infrastructure Maintenance", "Routine maintenance of the internal fibre backbone will take place between 10:00 and 12:00 on Thursday. No extended downtime anticipated.", 9),
            ("Indigenous Verge Landscaping Schedule", "Our quarterly indigenous planting initiative begins next Monday. Verge access will remain unobstructed throughout.", 3),
        ],
        "providers": [
            ("provider.sr01@example.com", "Sipho Dlamini", "plumbing", "0821110001", True),
            ("provider.sr02@example.com", "Marius Botha", "electrical", "0821110002", True),
        ],
        "image_assets": [
            ("silverleaf-reserve-01-hero.jpg", "Silverleaf Reserve — Aerial landscape view of contemporary luxury units"),
            ("silverleaf-reserve-02-entrance.jpg", "Silverleaf Reserve — Dual-lane secure gatehouse and boom control"),
            ("silverleaf-reserve-03-amenities.jpg", "Silverleaf Reserve — Resident clubhouse with lap pool and deck"),
            ("silverleaf-reserve-04-infrastructure.jpg", "Silverleaf Reserve — Paved pedestrian walkway and path lighting"),
        ],
        "ai_suggestions": [
            {
                "complaint_idx": 0,
                "category": "water",
                "priority": "urgent",
                "trade": "plumber",
                "decision": "accepted",
            },
            {
                "complaint_idx": 1,
                "category": "gardens",
                "priority": "low",
                "trade": "landscaping",
                "decision": "accepted",
            },
        ],
    },
    {
        "key": "WM",
        "name": "Willowbrook Mews",
        "suburb": "Fourways",
        "city": "Johannesburg",
        "province": "Gauteng",
        "street": "Willowbrook Way",
        "description": "A well-managed 18-unit townhouse complex in Fourways with disciplined body corporate governance, orderly carport facilities, and reliable maintenance turnaround.",
        "admin": ("hoa.willowbrook@example.com", "David Ndlovu"),
        "unit_count": 18,
        "resident_count": 15,
        "unit_prefix": "WM",
        "complaint_target": 14,
        "resolved_target": 11,
        "avg_res_days": (2.4, 4.8),
        "wo_target": 11,
        "wo_completed": 9,
        "ratings": [4, 5, 4, 4, 5, 4, 4, 5, 4],
        "incidents": [
            ("suspicious_activity", "low", "resolved", 60, 3),
            ("access_control_failure", "medium", "resolved", 25, 2),
        ],
        "announcements": [
            ("Refuse Collection Day Adjustment", "Municipal waste collection moves to Wednesday mornings. Please ensure wheelie bins are placed outside carports by 07:00.", 21),
            ("Perimeter Electric Fence Inspection", "Technicians will conduct annual voltage and earthing tests on the perimeter fence this Friday.", 11),
            ("Communal Lawn and Pergola Courtesy", "Residents are kindly reminded that communal courtyard hours conclude at 21:00 on weekdays.", 4),
        ],
        "providers": [
            ("provider.wm01@example.com", "Thabo Molefe", "general", "0821110003", False),
            ("provider.wm02@example.com", "Johan van Wyk", "plumbing", "0821110004", True),
        ],
        "image_assets": [
            ("willowbrook-mews-01-hero.jpg", "Willowbrook Mews — Two-storey greige duplex townhouses"),
            ("willowbrook-mews-02-entrance.jpg", "Willowbrook Mews — Automated steel sliding gate and guardhouse"),
            ("willowbrook-mews-03-amenities.jpg", "Willowbrook Mews — Communal courtyard and garden benches"),
            ("willowbrook-mews-04-infrastructure.jpg", "Willowbrook Mews — Orderly carport bays and interlocking paving"),
        ],
        "ai_suggestions": [
            {
                "complaint_idx": 0,
                "category": "security",
                "priority": "urgent",
                "trade": "general_maintenance",
                "decision": "accepted",
            },
            {
                "complaint_idx": 1,
                "category": "noise",
                "priority": "low",
                "trade": None,
                "decision": "dismissed",
            },
        ],
    },
    {
        "key": "LG",
        "name": "Lakeside Gardens",
        "suburb": "Centurion",
        "city": "Tshwane",
        "province": "Gauteng",
        "street": "Lakeside Road",
        "description": "An established 20-unit residential complex in Centurion featuring mature shade trees, facing mixed operational performance and occasional maintenance backlogs.",
        "admin": ("hoa.lakeside@example.com", "Kabelo Sithole"),
        "unit_count": 20,
        "resident_count": 18,
        "unit_prefix": "LG",
        "complaint_target": 24,
        "resolved_target": 14,
        "avg_res_days": (6.5, 11.5),
        "wo_target": 15,
        "wo_completed": 9,
        "ratings": [3, 4, 3, 3, 4, 3, 4, 3, 3],
        "incidents": [
            ("vandalism", "medium", "resolved", 72, 7),
            ("trespass", "medium", "resolved", 48, 5),
            ("access_control_failure", "high", "investigating", 30, None),
            ("suspicious_activity", "low", "resolved", 14, 3),
        ],
        "announcements": [
            ("Stormwater Drainage Clearance Delay", "Contractors have completed phase one of the driveway culvert desilting. Phase two is delayed due to weather.", 24),
            ("Communal Swimming Pool Pump Overhaul", "The main filtration pump has been removed for workshop refurbishment; pool reopens next week.", 12),
            ("Municipal Water Pressure Warning", "Low pressure reported on the upper ring main; municipal maintenance logged under ref #84920.", 5),
        ],
        "providers": [
            ("provider.lg01@example.com", "Piet Botha", "electrical", "0821110005", False),
            ("provider.lg02@example.com", "Lerato Khumalo", "gardens", "0821110006", False),
        ],
        "image_assets": [
            ("lakeside-gardens-01-hero.jpg", "Lakeside Gardens — Established face-brick townhouse complex"),
            ("lakeside-gardens-02-entrance.jpg", "Lakeside Gardens — Faded automated gate and brick guard booth"),
            ("lakeside-gardens-03-amenities.jpg", "Lakeside Gardens — Communal swimming pool with brick surround"),
            ("lakeside-gardens-04-infrastructure.jpg", "Lakeside Gardens — Tarmac driveway with asphalt patching"),
        ],
        "ai_suggestions": [
            {
                "complaint_idx": 0,
                "category": "infrastructure",
                "priority": "high",
                "trade": "general_maintenance",
                "decision": "accepted",
            },
            {
                "complaint_idx": 1,
                "category": "administrative",
                "priority": "low",
                "trade": None,
                "decision": None,
            },
        ],
    },
    {
        "key": "EC",
        "name": "Eastbank Court",
        "suburb": "Bellville",
        "city": "Cape Town",
        "province": "Western Cape",
        "street": "Eastbank Avenue",
        "description": "An ageing 16-unit walk-up apartment complex in Bellville experiencing operational pressures, deferred maintenance backlogs, and prolonged issue turnaround.",
        "admin": ("hoa.eastbank@example.com", "Pieter van Wyk"),
        "unit_count": 16,
        "resident_count": 14,
        "unit_prefix": "EC",
        "complaint_target": 40,
        "resolved_target": 12,
        "avg_res_days": (16.0, 24.0),
        "wo_target": 18,
        "wo_completed": 6,
        "ratings": [2, 3, 2, 2, 3, 2],
        "incidents": [
            ("access_control_failure", "high", "resolved", 82, 14),
            ("theft", "high", "resolved", 66, 10),
            ("suspicious_activity", "medium", "investigating", 45, None),
            ("vandalism", "medium", "investigating", 35, None),
            ("access_control_failure", "critical", "open", 22, None),
            ("perimeter_breach", "high", "investigating", 15, None),
            ("theft", "medium", "open", 7, None),
        ],
        "announcements": [
            ("Common Property Lighting & Circuit Update", "Electricians have identified underground conduit faults causing stairwell outages. Quote pending approval.", 19),
            ("Water Header Tank Diagnostic Inspection", "Specialists are assessing corrosion on the rooftop header tank. Pressure fluctuations may occur.", 8),
        ],
        "providers": [
            ("provider.ec01@example.com", "Andries Grobbelaar", "general", "0821110007", False),
            ("provider.ec02@example.com", "Musa Ndlovu", "plumbing", "0821110008", False),
        ],
        "image_assets": [
            ("eastbank-court-01-hero.jpg", "Eastbank Court — Ageing walk-up apartment blocks with worn facade"),
            ("eastbank-court-02-entrance.jpg", "Eastbank Court — Weathered manual steel gate and outdated intercom"),
            ("eastbank-court-03-amenities.jpg", "Eastbank Court — Neglected courtyard with patchy grass"),
            ("eastbank-court-04-infrastructure.jpg", "Eastbank Court — Cracked exterior plaster and downpipe staining"),
        ],
        "ai_suggestions": [
            {
                "complaint_idx": 0,
                "category": "electrical",
                "priority": "normal",
                "trade": "electrician",
                "decision": "overridden",
            },
            {
                "complaint_idx": 1,
                "category": "water",
                "priority": "urgent",
                "trade": "plumber",
                "decision": None,
            },
        ],
    },
    {
        "key": "QV",
        "name": "Quarry View Flats",
        "suburb": "Salt Rock",
        "city": "Ballito",
        "province": "KwaZulu-Natal",
        "street": "Quarry Road",
        "description": "A high-density 12-unit residential complex under acute operational strain with substantial maintenance backlogs and persistent infrastructure failures.",
        "admin": ("hoa.quarryview@example.com", "Zanele Cele"),
        "unit_count": 12,
        "resident_count": 14,
        "unit_prefix": "QV",
        "complaint_target": 62,
        "resolved_target": 12,
        "avg_res_days": (25.5, 28.8),
        "wo_target": 22,
        "wo_completed": 5,
        "ratings": [2, 1, 2, 2, 1],
        "incidents": [
            ("perimeter_breach", "critical", "resolved", 85, 12),
            ("theft", "high", "resolved", 74, 9),
            ("access_control_failure", "high", "resolved", 65, 8),
            ("trespass", "high", "investigating", 55, None),
            ("vandalism", "medium", "investigating", 48, None),
            ("suspicious_activity", "medium", "investigating", 40, None),
            ("theft", "high", "investigating", 33, None),
            ("access_control_failure", "critical", "investigating", 28, None),
            ("perimeter_breach", "critical", "open", 22, None),
            ("theft", "high", "open", 17, None),
            ("trespass", "medium", "open", 12, None),
            ("vandalism", "medium", "open", 8, None),
            ("suspicious_activity", "medium", "open", 3, None),
        ],
        "announcements": [
            ("Urgent Notice: Main Sewage Sump Overflow", "Emergency bypass installed while pump impellers are re-machined. Keep ground-floor windows closed.", 16),
            ("Vehicle Security Advisory", "Multiple break-ins reported in open carport bays overnight. Body Corporate urges residents to remove all valuables.", 6),
        ],
        "providers": [
            ("provider.qv01@example.com", "Bongani Zwane", "plumbing", "0821110009", False),
            ("provider.qv02@example.com", "Tshepo Mabaso", "electrical", "0821110010", False),
        ],
        "image_assets": [
            ("quarry-view-flats-01-hero.jpg", "Quarry View Flats — Dense 3-storey walk-up block"),
            ("quarry-view-flats-02-entrance.jpg", "Quarry View Flats — Precast concrete perimeter and steel gate"),
            ("quarry-view-flats-03-amenities.jpg", "Quarry View Flats — Hard-packed dirt yard and clothesline poles"),
            ("quarry-view-flats-04-infrastructure.jpg", "Quarry View Flats — Weathered concrete stairwell and drainage channel"),
        ],
        "ai_suggestions": [
            {
                "complaint_idx": 0,
                "category": "security",
                "priority": "urgent",
                "trade": "security",
                "decision": None,
            },
            {
                "complaint_idx": 1,
                "category": "water",
                "priority": "urgent",
                "trade": "plumber",
                "decision": None,
            },
        ],
    },
]

_COMMON_COMPLAINT_TEMPLATES = (
    ("water", "urgent", "Burst municipal feeder pipe flooding front walkway and garden."),
    ("security", "high", "Perimeter gate motor slipping; gate fails to latch securely at night."),
    ("electrical", "normal", "Common property exterior lighting flickering and tripping circuit breaker."),
    ("infrastructure", "high", "Stormwater channel blocked with debris causing runoff backflow."),
    ("waste", "normal", "Refuse collection missed; bins overflowing near vehicle entrance."),
    ("gardens", "low", "Communal irrigation head misaligned, spraying boundary wall."),
    ("noise", "low", "Loud music playing in parking bays after permissible hours."),
    ("parking", "low", "Unauthorised commercial vehicle parked in allocated visitor bay."),
    ("administrative", "low", "Quarterly levy statement dispute regarding maintenance reserve fee."),
    ("water", "high", "Hot water cylinder leak in roof space causing ceiling damp."),
    ("electrical", "urgent", "Main distribution board sparking during peak evening loads."),
    ("security", "urgent", "Perimeter electric fence wire severed along north boundary."),
    ("infrastructure", "normal", "Deep asphalt pothole developed at complex entrance apron."),
    ("other", "low", "Complex directional signage weathered and illegible at night."),
)

_COMPLETION_NOTES = (
    "Repaired fractured copper pipe, replaced brass fittings, and pressure-tested line.",
    "Installed heavy-duty gate motor bracket, calibrated limit switches, and re-aligned track.",
    "Replaced luminaire ballast, renewed waterproof casing, and balanced electrical phase load.",
    "Cleared blocked stormwater gulley and restored gradient drainage.",
    "Refitted irrigation nozzles and reset electronic controller timers.",
    "Overhauled main circuit breaker and tested earth leakage protection.",
)


def demo_accounts() -> list[dict[str, str]]:
    """The demo sign-in accounts table."""
    accounts = []
    for cfg in COMPLEX_CONFIGS:
        admin_email, admin_name = cfg["admin"]
        accounts.append({"role": UserRole.hoa_admin.value, "email": admin_email, "full_name": admin_name})
    return accounts


def demo_user_specs() -> tuple[tuple[str, str, str], ...]:
    return tuple((a["email"], a["full_name"], a["role"]) for a in demo_accounts())


def _new_user(*, email: str, full_name: str, role: str, password_hash: str) -> User:
    return User(
        full_name=full_name,
        email=email,
        password_hash=password_hash,
        role=role,
        hoa_approved=True,
        email_verified=True,
    )


async def seed_demo(
    db: AsyncSession,
    *,
    expect_database: str,
    upload_dir: str | Path | None = None,
    image_dir: str | Path | None = None,
) -> dict[str, object]:
    """Provision all five fictional South African demo complexes."""
    target = await current_database_name(db)
    validate_seed_target(target, expect_database=expect_database)

    # Check if any complex already exists
    existing = await db.execute(
        select(Estate).where(Estate.name.in_(DEMO_ESTATE_NAMES))
    )
    existing_estates = existing.scalars().all()
    if len(existing_estates) == len(DEMO_ESTATE_NAMES):
        return {
            "created": False,
            "database": target,
            "estate": DEMO_ESTATE_NAME,
            "estate_id": existing_estates[0].estate_id,
            "users": demo_accounts(),
            "message": f"All 5 demo complexes already exist in {target} — nothing changed.",
        }

    anchor = _anchor()
    password_hash = hash_password(_demo_password())
    repo_root = Path(__file__).resolve().parents[2]
    asset_dir = Path(image_dir) if image_dir is not None else repo_root / "estate-demo-images"

    estates_summary = []
    all_users = []

    # Seeding each complex in order
    for cfg in COMPLEX_CONFIGS:
        est_name = cfg["name"]
        existing_check = await db.execute(select(Estate).where(Estate.name == est_name))
        existing_row = existing_check.scalar_one_or_none()
        if existing_row is not None:
            continue

        # 1. Estate entity
        estate = Estate(
            name=est_name,
            suburb=cfg["suburb"],
            city=cfg["city"],
            province=cfg["province"],
            description=cfg["description"],
            is_demo=False,
            is_public=True,
            show_living_score=True,
            created_at=_ago(anchor, DEMO_HISTORY_DAYS),
        )
        db.add(estate)
        await db.flush()

        # 2. HOA Administrator
        admin_email, admin_name = cfg["admin"]
        admin_user = _new_user(
            email=admin_email,
            full_name=admin_name,
            role=UserRole.hoa_admin.value,
            password_hash=password_hash,
        )
        db.add(admin_user)
        await db.flush()
        all_users.append({"role": UserRole.hoa_admin.value, "email": admin_email, "full_name": admin_name})

        # Administrator estate membership
        db.add(
            EstateMembership(
                user_id=admin_user.user_id,
                estate_id=estate.estate_id,
                property_id=None,
                membership_role=UserRole.hoa_admin.value,
            )
        )

        # 3. Units
        units: list[Property] = []
        for u_idx in range(1, cfg["unit_count"] + 1):
            unit_no = f"{cfg['unit_prefix']}-{u_idx:02d}"
            size = Decimal(str(85 + (u_idx % 6) * 25))
            beds = 2 + (u_idx % 3)
            baths = 1 + (u_idx % 2)
            prop = Property(
                estate_id=estate.estate_id,
                unit_no=unit_no,
                complex_name=est_name,
                street_address=f"{u_idx} {cfg['street']}",
                suburb=cfg["suburb"],
                size_m2=size,
                bedrooms=beds,
                bathrooms=baths,
            )
            units.append(prop)
            db.add(prop)
        await db.flush()

        # 4. Residents
        residents: list[User] = []
        occupancies: list[tuple[User, Property]] = []
        first_names = ("Thandi", "Sipho", "Lerato", "Pieter", "Aisha", "Johan", "Nomvula", "Kabelo",
                       "Maria", "Tebogo", "Annelie", "Musa", "Zanele", "Riaan", "Precious", "Bongani",
                       "Elmarie", "Tshepo", "Ntombi", "Andries")
        last_names = ("Nkosi", "Mokoena", "Dlamini", "van Wyk", "Patel", "Botha", "Molefe", "Sithole",
                      "Naidoo", "Khumalo", "Fourie", "Ndlovu", "Mahlangu", "Pretorius", "Cele", "Zwane",
                      "Mabaso", "Ndlangamandla", "September", "Grobbelaar")

        for r_idx in range(cfg["resident_count"]):
            r_email = f"resident.{cfg['key'].lower()}{r_idx + 1:02d}@{DEMO_EMAIL_DOMAIN}"
            fn = first_names[(r_idx + len(cfg['key'])) % len(first_names)]
            ln = last_names[(r_idx * 3) % len(last_names)]
            res_user = _new_user(
                email=r_email,
                full_name=f"{fn} {ln}",
                role=UserRole.resident.value,
                password_hash=password_hash,
            )
            db.add(res_user)
            residents.append(res_user)
        await db.flush()

        # Unit assignments & memberships
        for r_idx, resident in enumerate(residents):
            unit = units[r_idx % len(units)]
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

        # 5. Service Providers
        providers: list[ServiceProvider] = []
        for p_email, p_name, p_trade, p_phone, p_emg in cfg["providers"]:
            p_user = _new_user(
                email=p_email,
                full_name=p_name,
                role=UserRole.service_provider.value,
                password_hash=password_hash,
            )
            db.add(p_user)
            await db.flush()
            all_users.append({"role": UserRole.service_provider.value, "email": p_email, "full_name": p_name})

            db.add(
                EstateMembership(
                    user_id=p_user.user_id,
                    estate_id=estate.estate_id,
                    property_id=None,
                    membership_role=UserRole.service_provider.value,
                )
            )

            prov_profile = ServiceProvider(
                user_id=p_user.user_id,
                full_name=p_name,
                trade=p_trade,
                phone=p_phone,
                email=p_email,
                verified=True,
                emergency_available=p_emg,
                total_reviews=0,
            )
            db.add(prov_profile)
            providers.append(prov_profile)
        await db.flush()

        # 6. Join code
        join_code_str = generate_join_code()
        db.add(
            EstateJoinCode(
                estate_id=estate.estate_id,
                code=join_code_str,
                created_by=admin_user.user_id,
                created_at=_ago(anchor, DEMO_HISTORY_DAYS),
                expires_at=None,
                revoked_at=None,
            )
        )

        # 7. Complaints
        complaints: list[Complaint] = []
        total_complaints = cfg["complaint_target"]
        in_win_target = cfg.get("in_window", total_complaints)
        resolved_count = cfg["resolved_target"]
        min_res, max_res = cfg["avg_res_days"]

        for c_idx in range(total_complaints):
            cat, prio, desc = _COMMON_COMPLAINT_TEMPLATES[c_idx % len(_COMMON_COMPLAINT_TEMPLATES)]
            if c_idx < in_win_target:
                created_days_ago = 86.0 - (c_idx * (84.0 / max(in_win_target - 1, 1)))
            else:
                created_days_ago = 93.0 + (c_idx - in_win_target) * 7.0
            created = _ago(anchor, created_days_ago)

            res_days = min_res + ((max_res - min_res) * (c_idx % 5) / 4.0)
            reviewed = created + timedelta(hours=6)
            assigned = reviewed + timedelta(hours=10)
            started = assigned + timedelta(hours=12)
            resolved = started + timedelta(days=res_days)

            if c_idx < resolved_count:
                # Resolved complaints: half are rated by resident
                status = ComplaintStatus.rated.value if (c_idx % 2 == 0) else ComplaintStatus.resolved.value
            elif c_idx < resolved_count + max(1, (in_win_target - resolved_count) // 2):
                status = ComplaintStatus.in_progress.value
            elif c_idx < in_win_target - 1:
                status = ComplaintStatus.assigned.value
            else:
                status = ComplaintStatus.submitted.value

            complainant, unit = occupancies[c_idx % len(occupancies)]
            complaint = Complaint(
                user_id=complainant.user_id,
                estate_id=estate.estate_id,
                unit_id=unit.unit_id,
                category=cat,
                description=desc,
                priority=prio,
                is_anonymous=False,
                status=status,
                created_at=created,
                reviewed_at=None if status == ComplaintStatus.submitted.value else reviewed,
                assigned_at=assigned if status in (ComplaintStatus.assigned.value, ComplaintStatus.in_progress.value, ComplaintStatus.resolved.value, ComplaintStatus.rated.value) else None,
                started_at=started if status in (ComplaintStatus.in_progress.value, ComplaintStatus.resolved.value, ComplaintStatus.rated.value) else None,
                resolved_at=resolved if status in (ComplaintStatus.resolved.value, ComplaintStatus.rated.value) else None,
            )
            db.add(complaint)
            complaints.append(complaint)
        await db.flush()

        # Complaint lifecycle events
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
                ("reviewed", ComplaintStatus.submitted.value, ComplaintStatus.reviewed.value, complaint.reviewed_at, admin_user.user_id),
                ("assigned", ComplaintStatus.reviewed.value, ComplaintStatus.assigned.value, complaint.assigned_at, admin_user.user_id),
                ("in_progress", ComplaintStatus.assigned.value, ComplaintStatus.in_progress.value, complaint.started_at, admin_user.user_id),
                ("resolved", ComplaintStatus.in_progress.value, ComplaintStatus.resolved.value, complaint.resolved_at, admin_user.user_id),
                ("rated", ComplaintStatus.resolved.value, ComplaintStatus.rated.value, complaint.resolved_at, complaint.user_id),
            )
            for ev_type, f_st, t_st, occ_at, actor in transitions:
                if occ_at is None:
                    continue
                if ev_type == "rated" and complaint.status != ComplaintStatus.rated.value:
                    continue
                db.add(
                    ComplaintEvent(
                        complaint_id=complaint.complaint_id,
                        estate_id=estate.estate_id,
                        actor_user_id=actor,
                        event_type=ev_type,
                        from_status=f_st,
                        to_status=t_st,
                        occurred_at=occ_at,
                        note="Status progressed via HOA operational review.",
                    )
                )

        # 8. Work Orders & Resident Reviews
        work_orders: list[MaintenanceworkOrder] = []
        wo_target = min(cfg["wo_target"], len(complaints))
        wo_completed_count = cfg["wo_completed"]
        ratings_list = cfg["ratings"]

        for wo_idx in range(wo_target):
            complaint = complaints[wo_idx]
            provider = providers[wo_idx % len(providers)]
            is_completed = wo_idx < wo_completed_count

            assigned_at = complaint.assigned_at or complaint.created_at
            resolved_at = complaint.resolved_at or (assigned_at + timedelta(days=2))
            rating = ratings_list[wo_idx % len(ratings_list)] if is_completed else None

            wo = MaintenanceworkOrder(
                complaint_id=complaint.complaint_id,
                estate_id=estate.estate_id,
                provider_id=provider.provider_id,
                status=WorkOrderStatus.completed.value if is_completed else WorkOrderStatus.in_progress.value,
                job_cost=Decimal(650 + (wo_idx % 5) * 280) + Decimal("0.50"),
                resident_rating=rating,
                completion_notes=_COMPLETION_NOTES[wo_idx % len(_COMPLETION_NOTES)] if is_completed else None,
                assigned_at=assigned_at,
                resolved_at=resolved_at if is_completed else None,
                actual_completion_date=resolved_at if is_completed else None,
                estimated_completion_date=assigned_at + timedelta(days=3),
            )
            db.add(wo)
            work_orders.append(wo)

        # Provider review rows
        ratings_by_prov: dict[int, list[int]] = {}
        for r_idx, (prov, r_val) in enumerate([(providers[i % len(providers)], val) for i, val in enumerate(ratings_list[:min(5, len(ratings_list))])]):
            db.add(
                Review(
                    user_id=residents[r_idx % len(residents)].user_id,
                    provider_id=prov.provider_id,
                    rating=r_val,
                    comment="Satisfactory completion of work order specification.",
                    created_at=_ago(anchor, 15 + r_idx * 5),
                )
            )
            ratings_by_prov.setdefault(prov.provider_id, []).append(r_val)

        for prov in providers:
            p_ratings = ratings_by_prov.get(prov.provider_id, [4])
            prov.total_reviews = len(p_ratings)
            prov.avg_rating = (Decimal(sum(p_ratings)) / Decimal(len(p_ratings))).quantize(Decimal("0.01"))

        # 9. Security Incidents
        for inc_idx, (cat, sev, st, days_ago, res_days) in enumerate(cfg["incidents"]):
            occ_at = _ago(anchor, days_ago, hours=3)
            res_at = occ_at + timedelta(days=res_days) if res_days is not None else None
            db.add(
                SecurityIncident(
                    estate_id=estate.estate_id,
                    property_id=units[inc_idx % len(units)].unit_id if inc_idx % 2 == 0 else None,
                    category=cat,
                    severity=sev,
                    status=st,
                    occurred_at=occ_at,
                    resolved_at=res_at,
                    resolution_notes="Patrol report logged and access perimeter inspected." if res_at else None,
                    created_by=admin_user.user_id,
                )
            )

        # 10. Announcements
        for a_title, a_msg, a_days in cfg["announcements"]:
            db.add(
                Announcement(
                    estate_id=estate.estate_id,
                    title=a_title,
                    message=a_msg,
                    created_by=admin_user.user_id,
                    created_at=_ago(anchor, a_days),
                )
            )

        # Commit the real operational records before uploading photos and
        # computing scores. AI triage is deliberately never pre-populated.
        await db.commit()

        # 12. Photographs
        photo_service = EstatePhotoService(db, upload_dir=upload_dir)
        imported_photos = []

        for p_idx, (filename, caption) in enumerate(cfg["image_assets"]):
            asset_path = asset_dir / filename
            if asset_path.exists() and asset_path.is_file():
                try:
                    img_data = asset_path.read_bytes()
                    photo_record = await photo_service.upload_photo(
                        admin_user,
                        estate_id=estate.estate_id,
                        filename=filename,
                        content_type="image/jpeg",
                        data=img_data,
                        caption=caption,
                    )
                    imported_photos.append(photo_record)
                except Exception as ex:
                    print(f"Warning: could not upload image {filename}: {ex}")

        # 13. Living Score Snapshots
        score_snapshots = []
        for offset in DEMO_SCORE_AS_OF_OFFSETS:
            snap = await snapshot_estate_living_score(
                db, estate.estate_id, as_of=_ago(anchor, offset)
            )
            score_snapshots.append(
                {
                    "as_of": snap.as_of.isoformat(),
                    "status": snap.status,
                    "overall_score": None if snap.overall_score is None else str(snap.overall_score),
                    "engine_version": snap.engine_version,
                    "components": {
                        "resolution": str(snap.resolution_score) if snap.resolution_score is not None else None,
                        "frequency": str(snap.frequency_score) if snap.frequency_score is not None else None,
                        "security": str(snap.security_score) if snap.security_score is not None else None,
                        "satisfaction": str(snap.satisfaction_score) if snap.satisfaction_score is not None else None,
                        "infrastructure": str(snap.infrastructure_score) if snap.infrastructure_score is not None else None,
                    },
                }
            )

        estates_summary.append(
            {
                "estate": estate.name,
                "estate_id": estate.estate_id,
                "properties": len(units),
                "residents": len(residents),
                "providers": len(providers),
                "complaints": len(complaints),
                "work_orders": len(work_orders),
                "incidents": len(cfg["incidents"]),
                "announcements": len(cfg["announcements"]),
                "photos": len(imported_photos),
                "join_code": join_code_str,
                "scores": score_snapshots,
            }
        )

    first_estate = estates_summary[0] if estates_summary else {}

    return {
        "created": True,
        "database": target,
        "estates": estates_summary,
        "estate": first_estate.get("estate", DEMO_ESTATE_NAME),
        "estate_id": first_estate.get("estate_id", 1),
        "users": demo_accounts(),
        "properties": first_estate.get("properties", 24),
        "residents": first_estate.get("residents", 20),
        "providers": first_estate.get("providers", 2),
        "complaints": first_estate.get("complaints", 11),
        "work_orders": first_estate.get("work_orders", 13),
        "incidents": first_estate.get("incidents", 1),
        "announcements": first_estate.get("announcements", 3),
        "photos": first_estate.get("photos", 4),
        "scores": first_estate.get("scores", []),
    }


async def count_demo_ai_rows(db: AsyncSession) -> dict[str, int]:
    """Count how many AI rows exist in the database."""
    from app.analytics.models.ai_insight import AIInsight
    insights = await db.execute(select(func.count()).select_from(AIInsight))
    suggestions = await db.execute(select(func.count()).select_from(ComplaintAISuggestion))
    return {
        "ai_insights": int(insights.scalar_one()),
        "ai_suggestions": int(suggestions.scalar_one()),
    }


__all__ = [
    "COMPLEX_CONFIGS",
    "DEFAULT_DEMO_PASSWORD",
    "DEMO_EMAIL_DOMAIN",
    "DEMO_ESTATE_NAME",
    "DEMO_ESTATE_NAMES",
    "DEMO_HISTORY_DAYS",
    "DEMO_SCORE_AS_OF_OFFSETS",
    "SeedGuardError",
    "count_demo_ai_rows",
    "current_database_name",
    "demo_accounts",
    "demo_user_specs",
    "placeholder_jpeg",
    "seed_demo",
    "validate_seed_target",
]
