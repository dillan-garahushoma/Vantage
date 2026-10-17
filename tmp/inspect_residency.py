"""Read-only look at the live dev database. Prints no secrets, updates nothing."""
import asyncio

from sqlalchemy import text

from app.db.session import AsyncSessionLocal


async def main() -> None:
    async with AsyncSessionLocal() as db:
        version = (await db.execute(text("SELECT version_num FROM alembic_version"))).scalar_one()
        print("alembic version:", version)

        print("\n-- estates --")
        rows = await db.execute(
            text(
                "SELECT estate_id, name, is_demo, is_public, show_living_score "
                "FROM estates ORDER BY estate_id"
            )
        )
        for row in rows:
            print(dict(row._mapping))

        print("\n-- tables of interest --")
        rows = await db.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' AND (table_name LIKE '%residency%' "
                "OR table_name LIKE '%living%' OR table_name LIKE '%membership%' "
                "OR table_name LIKE '%ai_%' OR table_name LIKE '%suggestion%') "
                "ORDER BY table_name"
            )
        )
        for row in rows:
            print(" ", row[0])

        print("\n-- residency requests --")
        rows = await db.execute(
            text(
                "SELECT request_id, estate_id, user_id, unit_no, status, applicant_name, "
                "decided_by, decided_at, created_at FROM estate_residency_requests "
                "ORDER BY request_id"
            )
        )
        rows = list(rows)
        if not rows:
            print("  (none)")
        for row in rows:
            print(dict(row._mapping))

        print("\n-- memberships per estate/role --")
        rows = await db.execute(
            text(
                "SELECT estate_id, membership_role, count(*) AS n, "
                "count(*) FILTER (WHERE property_id IS NULL) AS no_unit "
                "FROM estate_memberships GROUP BY estate_id, membership_role "
                "ORDER BY estate_id, membership_role"
            )
        )
        for row in rows:
            print(dict(row._mapping))

        print("\n-- users by role --")
        rows = await db.execute(
            text("SELECT role, count(*) FROM users GROUP BY role ORDER BY role")
        )
        for row in rows:
            print(tuple(row))


asyncio.run(main())
