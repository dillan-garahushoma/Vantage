"""Command-line utilities for VALORA."""

import argparse
import asyncio
import json
from pathlib import Path

from app.main import app


def export_openapi() -> Path:
    output_path = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path


async def _seed_demo_async(*, expect_database: str) -> dict:
    from app.db.session import AsyncSessionLocal
    from app.seed_demo import seed_demo

    async with AsyncSessionLocal() as session:
        return await seed_demo(session, expect_database=expect_database)


def _print_credentials_table(users: list[dict]) -> None:
    """The demo sign-in table, printed once. Never a password value."""
    print("  sign-in accounts (demo database only):")
    print(f"    {'role':<17} {'email':<28} name")
    for user in users:
        print(f"    {user['role']:<17} {user['email']:<28} {user['full_name']}")
    print("    password: VALORA_SEED_PASSWORD if you set one, otherwise the local")
    print("              demo default in app/seed_demo.py (see docs/GETTING_STARTED.md).")


def seed_demo_command(*, expect_database: str) -> None:
    """Provision the local demo estate (guarded and idempotent).

    Refuses to write unless the connected database is the one named by
    ``--expect-database`` and its name contains "demo". The demo password is
    never printed — set ``VALORA_SEED_PASSWORD`` to choose it.
    """
    from app.seed_demo import SeedGuardError

    try:
        result = asyncio.run(_seed_demo_async(expect_database=expect_database))
    except SeedGuardError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1) from exc

    if not result["created"]:
        print(result["message"])
        _print_credentials_table(result["users"])
        return

    if "estates" in result and result["estates"]:
        print(f"Seeded {len(result['estates'])} estates into database: {result['database']}")
        for est in result["estates"]:
            print(f"\n--- Estate: {est['estate']} (id={est['estate_id']}) ---")
            print(f"  units:       {est['properties']}")
            print(f"  residents:   {est['residents']}")
            print(f"  providers:   {est['providers']}")
            print(f"  complaints:  {est['complaints']}")
            print(f"  work orders: {est['work_orders']}")
            print(f"  incidents:   {est['incidents']}")
            print(f"  notices:     {est['announcements']}")
            print(f"  photos:      {est['photos']} imported")
            print(f"  join code:   {est['join_code']}")
            print("  Living Score snapshots (real engine, oldest first):")
            for score in est["scores"]:
                published = score["overall_score"] if score["overall_score"] is not None else "none"
                print(
                    f"    {score['as_of'][:10]}  status={score['status']:<17} "
                    f"score={published} engine={score['engine_version']}"
                )
    else:
        print(f"Seeded estate: {result['estate']} (id={result['estate_id']})")
        print(f"  database:    {result['database']}")
        print(f"  units:       {result['properties']}")
        print(f"  residents:   {result['residents']}")
        print(f"  providers:   {result['providers']}")
        print(f"  complaints:  {result['complaints']}")
        print(f"  work orders: {result['work_orders']}")
        print(f"  incidents:   {result['incidents']}")
        print(f"  notices:     {result['announcements']}")
        print(f"  photos:      {result['photos']} (generated placeholders, real pipeline)")
        print("  Living Score snapshots (real engine, oldest first):")
        for score in result["scores"]:
            published = score["overall_score"] if score["overall_score"] is not None else "none"
            print(
                f"    {score['as_of'][:10]}  status={score['status']:<17} "
                f"score={published} engine={score['engine_version']}"
            )
    _print_credentials_table(result["users"])


async def snapshot_estate_living_score(session, estate_id: int, *, as_of=None):
    """Bridge for the demo seeder to invoke the real Living Score engine without naming the service."""
    from app.analytics.services.estate_living_score_service import LivingScoreService

    return await LivingScoreService(session).calculate_and_snapshot(
        estate_id, actor=None, as_of=as_of
    )


async def _recalc_living_scores_async(*, estate_id: int | None, include_demo: bool):
    """Score every selected estate, with no actor: the scheduled-job path."""
    from app.analytics.services.estate_living_score_service import LivingScoreService
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        return await LivingScoreService(session).recalculate_estates(
            estate_id=estate_id, include_demo=include_demo
        )


def recalc_living_scores_command(*, estate_id: int | None = None, include_demo: bool = False) -> None:
    """Recompute the estate Living Score, one immutable snapshot per estate.

    Real estates only unless ``--include-demo`` is given. Prints one line per
    estate with its id, status, score and engine version - operational metadata
    only, never personal data - so a Windows Task Scheduler job can log the run.
    Idempotent in the sense that matters: each run appends, and no stored snapshot
    is ever rewritten. Set the cadence in the scheduler; there is no queue here.
    """
    scored = asyncio.run(
        _recalc_living_scores_async(estate_id=estate_id, include_demo=include_demo)
    )
    for snapshot in scored:
        score = "none" if snapshot.overall_score is None else snapshot.overall_score
        print(
            f"estate {snapshot.estate_id}: status={snapshot.status} "
            f"score={score} engine={snapshot.engine_version}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("export-openapi", help="write the deterministic OpenAPI contract")
    seed_parser = subparsers.add_parser(
        "seed-demo",
        help="create the idempotent local demo estate (refuses a non-demo database)",
    )
    seed_parser.add_argument(
        "--expect-database",
        required=True,
        help="the demo database this run must be connected to (name must contain 'demo')",
    )
    recalc = subparsers.add_parser(
        "recalc-living-scores",
        help="recompute the estate Living Score (one snapshot per estate)",
    )
    recalc.add_argument(
        "--estate-id", type=int, default=None, help="score a single estate only"
    )
    recalc.add_argument(
        "--include-demo",
        action="store_true",
        help="also score seeded demonstration estates (excluded by default)",
    )
    args = parser.parse_args()

    if args.command == "export-openapi":
        print(export_openapi())
    elif args.command == "seed-demo":
        seed_demo_command(expect_database=args.expect_database)
    elif args.command == "recalc-living-scores":
        recalc_living_scores_command(estate_id=args.estate_id, include_demo=args.include_demo)


if __name__ == "__main__":
    main()
