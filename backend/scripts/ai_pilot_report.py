"""Read-only AI usage report for one pilot estate (BATCH PILOT-1).

Answers "is the AI layer actually helping?" for a real pilot, without ever
touching the data it reports on:

* it **only ever sends ``SELECT``** statements (``read_only_statements()`` makes
  that auditable, and the tests assert it);
* it reads the **metadata-only** tables from AI-2/AI-3 - ``ai_call_events`` and
  ``complaint_ai_suggestions``. Neither table stores a prompt, a provider
  response or any resident-written text, so this report cannot print one;
* a table that does not exist yet is **skipped with a clear message** rather than
  crashing, so the report is useful on a database that is part-way through the
  migrations;
* it does **not** consult ``complaints`` or any other table holding resident
  text. Rates come from the suggestion rows' own labels.

The Health Brief sections belong to AI-4; this script reports that they are not
available yet and says why.

Usage::

    export DATABASE_URL="postgresql+asyncpg://user:pw@host:5432/valora_pilot"
    python scripts/ai_pilot_report.py --estate-id 1 --days 30
"""
from __future__ import annotations

import argparse
import asyncio
import math
import os
import sys
from collections import Counter
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.parse import urlsplit

# Allow "python scripts/ai_pilot_report.py" from the backend directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# --------------------------------------------------------------------------- #
# the only SQL this script can send
# --------------------------------------------------------------------------- #

# Every statement below is a SELECT over metadata-only columns. There is
# deliberately no statement that reads complaint text, a prompt or a response.
SELECT_TABLE_EXISTS = (
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_schema = current_schema() AND table_name = :name"
)
SELECT_AI_CALLS = (
    "SELECT feature, status, reason, latency_ms, created_at "
    "FROM ai_call_events "
    "WHERE estate_id = :estate_id AND created_at >= :since"
)
SELECT_TRIAGE = (
    "SELECT decision, decided_at, created_at "
    "FROM complaint_ai_suggestions "
    "WHERE estate_id = :estate_id AND created_at >= :since"
)

# The tables this report knows how to read.
CALL_LEDGER_TABLE = "ai_call_events"
TRIAGE_TABLE = "complaint_ai_suggestions"

# Owned by AI-4. Until that batch lands these tables do not exist; if they do
# exist, this script still does not read them (their shape is AI-4's to define).
BRIEF_TABLES: tuple[str, ...] = ("health_briefs", "health_brief_feedback")

# Below this n, a rate is an anecdote, not a measurement.
MIN_MEANINGFUL_N = 30


def read_only_statements() -> list[str]:
    """Every statement this module can send, for auditing and for tests."""
    return [SELECT_TABLE_EXISTS, SELECT_AI_CALLS, SELECT_TRIAGE]


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


def target_database_url() -> str:
    """Read the target from the environment (never from ``.env``)."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise ReportError(
            "DATABASE_URL is not set. Export it for this shell and re-run."
        )
    return url


def as_mapping(row: Any) -> Mapping[str, Any]:
    """Accept a SQLAlchemy Row, a mapping or a plain object uniformly."""
    if isinstance(row, Mapping):
        return row
    mapping = getattr(row, "_mapping", None)
    if mapping is not None:
        return mapping
    return vars(row)


def percentile_ms(values: Sequence[int], pct: float) -> int | None:
    """Nearest-rank percentile: the smallest value at or above ``pct`` percent."""
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(pct / 100 * len(ordered)) - 1)
    return ordered[index]


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# aggregation (pure - no database, no clock)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class LatencyStats:
    """Latency of the calls that were actually timed.

    ``count`` is the number of timed calls, which can be smaller than the number
    of call rows: a call rejected before it reached the provider has no latency.
    """

    count: int
    avg_ms: float | None = None
    p95_ms: int | None = None


def summarise_latency(values: Iterable[int]) -> LatencyStats:
    samples = [value for value in values if value is not None]
    if not samples:
        return LatencyStats(count=0)
    return LatencyStats(
        count=len(samples),
        avg_ms=round(sum(samples) / len(samples), 1),
        p95_ms=percentile_ms(samples, 95),
    )


def render_latency(stats: LatencyStats) -> str:
    if stats.count == 0 or stats.avg_ms is None:
        return "timed n=0  avg=-  p95=-"
    return f"timed n={stats.count}  avg={stats.avg_ms}ms  p95={stats.p95_ms}ms"


@dataclass(frozen=True)
class CallGroup:
    feature: str
    status: str
    reason: str
    count: int
    latency: LatencyStats


def summarise_call_rows(rows: Iterable[Any]) -> list[CallGroup]:
    """Group the append-only ledger by feature/status/reason."""
    counts: Counter[tuple[str, str, str]] = Counter()
    latencies: dict[tuple[str, str, str], list[int]] = {}
    for row in rows:
        data = as_mapping(row)
        key = (
            str(data.get("feature") or "<unknown>"),
            str(data.get("status") or "<unknown>"),
            str(data.get("reason") or "-"),
        )
        counts[key] += 1
        latency = _int_or_none(data.get("latency_ms"))
        if latency is not None:
            latencies.setdefault(key, []).append(latency)
    return [
        CallGroup(
            feature=feature,
            status=status,
            reason=reason,
            count=count,
            latency=summarise_latency(latencies.get((feature, status, reason), [])),
        )
        for (feature, status, reason), count in sorted(counts.items())
    ]


def render_calls(groups: Sequence[CallGroup]) -> str:
    if not groups:
        return "No AI calls recorded for this estate in the window."
    total = sum(group.count for group in groups)
    lines = [f"AI calls: {total} in the window"]
    for group in groups:
        lines.append(
            f"  {group.feature:<18} {group.status:<17} {group.reason:<18} "
            f"calls={group.count:<5} {render_latency(group.latency)}"
        )
    return "\n".join(lines)


@dataclass(frozen=True)
class TriageSummary:
    """What an HOA admin did with the advisory triage suggestions."""

    total: int
    counts: dict[str, int] = field(default_factory=dict)
    undecided: int = 0

    @property
    def decided(self) -> int:
        return sum(self.counts.values())

    def rate(self, decision: str) -> float | None:
        """Share of all suggestions with this decision, as a percentage."""
        if self.total == 0:
            return None
        return round(self.counts.get(decision, 0) * 100 / self.total, 1)

    @property
    def agreement_rate(self) -> float | None:
        """Of the decisions made, the share that simply accepted the suggestion."""
        if self.decided == 0:
            return None
        return round(self.counts.get("accepted", 0) * 100 / self.decided, 1)


def summarise_triage_rows(rows: Iterable[Any]) -> TriageSummary:
    counts: Counter[str] = Counter()
    total = 0
    undecided = 0
    for row in rows:
        data = as_mapping(row)
        decision = data.get("decision")
        total += 1
        if decision:
            counts[str(decision)] += 1
        else:
            undecided += 1
    return TriageSummary(total=total, counts=dict(counts), undecided=undecided)


def render_triage(summary: TriageSummary) -> str:
    if summary.total == 0:
        return (
            "Triage decisions: no suggestions recorded for this estate in the window "
            "(AI triage off, or nothing triaged yet)."
        )
    lines = [
        f"Triage decisions: {summary.total} suggestions, "
        f"{summary.decided} decided, {summary.undecided} undecided"
    ]
    for decision in ("accepted", "overridden", "dismissed"):
        count = summary.counts.get(decision, 0)
        rate = summary.rate(decision)
        lines.append(f"  {decision:<11} n={count:<5} {rate}% of suggestions")
    if summary.agreement_rate is not None:
        lines.append(
            f"  agreement (accepted of decided): {summary.agreement_rate}% "
            f"of n={summary.decided}"
        )
    if summary.total < MIN_MEANINGFUL_N:
        lines.append(
            f"  NOTE: n={summary.total} is below {MIN_MEANINGFUL_N}. Rates at this "
            "sample size are not meaningful - treat them as anecdotes, not evidence."
        )
    else:
        lines.append(
            f"  n={summary.total} supports a rough reading; "
            "it is still not a significance test."
        )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# reading (the only place a session is used)
# --------------------------------------------------------------------------- #


class ReportError(Exception):
    """Something the operator must fix before the report can be produced."""


async def table_exists(session: AsyncSession, name: str) -> bool:
    result = await session.execute(text(SELECT_TABLE_EXISTS), {"name": name})
    return result.scalar_one_or_none() is not None


async def fetch_call_rows(
    session: AsyncSession, *, estate_id: int, since: datetime
) -> list[Mapping[str, Any]]:
    result = await session.execute(
        text(SELECT_AI_CALLS), {"estate_id": estate_id, "since": since}
    )
    return [dict(row) for row in result.mappings().all()]


async def fetch_triage_rows(
    session: AsyncSession, *, estate_id: int, since: datetime
) -> list[Mapping[str, Any]]:
    result = await session.execute(
        text(SELECT_TRIAGE), {"estate_id": estate_id, "since": since}
    )
    return [dict(row) for row in result.mappings().all()]


# --------------------------------------------------------------------------- #
# the report
# --------------------------------------------------------------------------- #


@dataclass
class Section:
    title: str
    body: str
    skipped: bool = False


@dataclass
class Report:
    # The redacted target, so a report printed to a log says which database it read.
    target: str
    estate_id: int
    days: int
    sections: list[Section] = field(default_factory=list)

    def has_data(self) -> bool:
        return any(not section.skipped for section in self.sections)


async def build_report(
    session: AsyncSession,
    *,
    estate_id: int,
    days: int,
    target: str,
    now: datetime | None = None,
) -> Report:
    since = (now or datetime.now(timezone.utc)) - timedelta(days=days)
    report = Report(target=target, estate_id=estate_id, days=days)

    if await table_exists(session, CALL_LEDGER_TABLE):
        rows = await fetch_call_rows(session, estate_id=estate_id, since=since)
        report.sections.append(
            Section(
                title=f"AI calls ({CALL_LEDGER_TABLE}, last {days} days)",
                body=render_calls(summarise_call_rows(rows)),
            )
        )
    else:
        report.sections.append(
            Section(
                title=f"AI calls ({CALL_LEDGER_TABLE})",
                body=(
                    f"skipped: the table {CALL_LEDGER_TABLE} does not exist in this "
                    "database yet. Apply the migration for this database "
                    "(alembic -c alembic.ini upgrade head) and re-run."
                ),
                skipped=True,
            )
        )

    if await table_exists(session, TRIAGE_TABLE):
        rows = await fetch_triage_rows(session, estate_id=estate_id, since=since)
        report.sections.append(
            Section(
                title=f"Triage decisions ({TRIAGE_TABLE}, last {days} days)",
                body=render_triage(summarise_triage_rows(rows)),
            )
        )
    else:
        report.sections.append(
            Section(
                title=f"Triage decisions ({TRIAGE_TABLE})",
                body=(
                    f"skipped: the table {TRIAGE_TABLE} does not exist in this "
                    "database yet. Apply the migration for this database "
                    "(alembic -c alembic.ini upgrade head) and re-run."
                ),
                skipped=True,
            )
        )

    report.sections.append(await _brief_section(session))
    return report


async def _brief_section(session: AsyncSession) -> Section:
    """The Health Brief sections belong to AI-4, so they are never faked here."""
    present = [name for name in BRIEF_TABLES if await table_exists(session, name)]
    if present:
        body = (
            "not reported by this script: "
            + ", ".join(present)
            + " exist, but the Health Brief tables are defined and owned by BATCH "
            "AI-4. Read them there rather than guessing at their shape here."
        )
    else:
        body = (
            "not available yet: the Health Brief tables "
            f"({', '.join(BRIEF_TABLES)}) arrive in BATCH AI-4, so there is nothing "
            "to report for them in this build. This section is skipped on purpose "
            "rather than reported as zero, which would read as 'no feedback'."
        )
    return Section(title="Health Brief feedback (AI-4)", body=body, skipped=True)


def render_report(report: Report) -> str:
    lines = [
        f"AI pilot report - estate #{report.estate_id}, last {report.days} days",
        "(read-only: this script only ever sends SELECT statements)",
        "",
    ]
    for section in report.sections:
        lines.append(section.title)
        lines.append("-" * len(section.title))
        lines.append(section.body)
        lines.append("")
    if not report.has_data():
        lines.append(
            "Nothing to report: no AI table exists in this database yet. The AI "
            "layer is off for this environment, which is the intended default."
        )
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def positive_days(value: str) -> int:
    try:
        days = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a whole number of days") from None
    if days <= 0:
        raise argparse.ArgumentTypeError("--days must be greater than zero")
    return days


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only AI usage report for one pilot estate. Reports the AI-2 "
            "call ledger and AI-3 triage decisions; Health Brief sections arrive "
            "in AI-4."
        )
    )
    parser.add_argument("--estate-id", type=int, required=True, help="estate to report on")
    parser.add_argument(
        "--days", type=positive_days, default=30, help="window size in days (default 30)"
    )
    return parser


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


async def main(
    argv: Sequence[str] | None = None, *, session_factory: Callable | None = None
) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:  # argparse already printed the reason
        return int(exc.code or 0)

    try:
        url = target_database_url()
    except ReportError as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Target database: {redact_database_url(url)}")
    print("(credentials come from DATABASE_URL and are not shown)")
    print("")

    factory = session_factory or default_session_factory()
    async with factory() as session:
        report = await build_report(
            session,
            estate_id=args.estate_id,
            days=args.days,
            target=redact_database_url(url),
        )
    print(render_report(report), end="")
    return 0


def cli() -> int:
    return asyncio.run(main())


if __name__ == "__main__":
    raise SystemExit(cli())
