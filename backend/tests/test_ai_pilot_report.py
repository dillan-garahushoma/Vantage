"""Tests for the read-only AI pilot report (BATCH PILOT-1).

No database is touched. The CLI is driven through an injected fake session that
records every statement it is given, so "read-only" is asserted about the real
SQL the script sends, and "handles missing tables" is asserted about the real
skip paths rather than about a database that happens to be empty.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ai_pilot_report as report  # noqa: E402

# Captured at import, not hardcoded: the report reads the real clock, so a frozen
# literal would only leave the window assertion one day of slack before drifting.
NOW = dt.datetime.now(dt.timezone.utc)


# ------------------------------------------------------------------- fakes


class FakeResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def mappings(self):
        return self

    def all(self):
        return list(self._rows)

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class FakeSession:
    """Records statements; returns canned rows per statement kind."""

    def __init__(self, *, tables=(), call_rows=(), triage_rows=()):
        self.tables = set(tables)
        self.call_rows = list(call_rows)
        self.triage_rows = list(triage_rows)
        self.statements: list[str] = []
        self.params: list[dict] = []
        self.writes = 0
        self.commits = 0

    def add(self, *_args, **_kwargs):  # pragma: no cover - must never be called
        self.writes += 1

    async def flush(self):  # pragma: no cover - must never be called
        self.writes += 1

    async def commit(self):  # pragma: no cover - must never be called
        self.commits += 1

    async def execute(self, statement, params=None):
        sql = " ".join(str(statement).split())
        self.statements.append(sql)
        self.params.append(dict(params or {}))
        lowered = sql.lower()
        if "information_schema.tables" in lowered:
            name = (params or {}).get("name")
            return FakeResult([{"name": name}] if name in self.tables else [])
        if "from ai_call_events" in lowered:
            return FakeResult(self.call_rows)
        if "from complaint_ai_suggestions" in lowered:
            return FakeResult(self.triage_rows)
        return FakeResult([])


class FakeSessionFactory:
    def __init__(self, session):
        self.session = session
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


def call_row(feature, status, reason=None, latency_ms=None, created_at=None):
    return {
        "feature": feature,
        "status": status,
        "reason": reason,
        "latency_ms": latency_ms,
        "created_at": created_at or NOW,
    }


def triage_row(decision=None, decided_at=None):
    return {"decision": decision, "decided_at": decided_at, "created_at": NOW}


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://pilot_user:s3cret@localhost:5432/valora_pilot",
    )
    return monkeypatch


async def run(session, *argv: str) -> int:
    """Run the CLI with an injected session; DATABASE_URL is already set."""
    return await report.main(list(argv), session_factory=FakeSessionFactory(session))


ALL_TABLES = ("ai_call_events", "complaint_ai_suggestions")


# ------------------------------------------------------------- aggregation


def test_calls_are_grouped_by_feature_status_and_reason() -> None:
    rows = [
        call_row("complaint_triage", "ok", None, 120),
        call_row("complaint_triage", "ok", None, 240),
        call_row("complaint_triage", "provider_failed", "timeout", 900),
        call_row("complaint_triage", "rejected_policy", "personal_data", None),
        call_row("health_brief", "ok", None, 300),
    ]

    groups = report.summarise_call_rows(rows)
    keyed = {(g.feature, g.status, g.reason): g for g in groups}

    ok = keyed[("complaint_triage", "ok", "-")]
    assert ok.count == 2
    assert ok.latency.count == 2
    assert ok.latency.avg_ms == 180.0
    assert keyed[("complaint_triage", "provider_failed", "timeout")].count == 1
    # A row with no latency still counts as a call, but not as a timed call.
    rejected = keyed[("complaint_triage", "rejected_policy", "personal_data")]
    assert rejected.count == 1
    assert rejected.latency.count == 0
    assert rejected.latency.avg_ms is None
    assert keyed[("health_brief", "ok", "-")].count == 1


def test_p95_is_nearest_rank_and_ignores_missing_latency() -> None:
    rows = [
        call_row("f", "ok", None, value)
        for value in (10, 20, 30, 40, 50, 60, 70, 80, 90, 100)
    ] + [call_row("f", "ok", None, None)]

    (group,) = report.summarise_call_rows(rows)
    assert group.latency.count == 10
    assert group.latency.p95_ms == 100
    assert group.latency.avg_ms == 55.0


def test_p95_of_a_small_sample_is_the_highest_value() -> None:
    rows = [call_row("f", "ok", None, 11), call_row("f", "ok", None, 12)]

    (group,) = report.summarise_call_rows(rows)
    assert group.latency.p95_ms == 12


def test_statuses_without_latency_are_reported_with_a_dash() -> None:
    rendered = report.render_latency(report.LatencyStats(count=0))
    assert "-" in rendered


def test_triage_counts_rates_and_shows_n() -> None:
    rows = (
        [triage_row("accepted") for _ in range(6)]
        + [triage_row("overridden") for _ in range(3)]
        + [triage_row("dismissed") for _ in range(1)]
        + [triage_row(None) for _ in range(5)]
    )

    summary = report.summarise_triage_rows(rows)

    assert summary.total == 15
    assert summary.decided == 10
    assert summary.undecided == 5
    assert summary.counts == {"accepted": 6, "overridden": 3, "dismissed": 1}
    assert summary.rate("accepted") == 40.0
    assert summary.rate("overridden") == 20.0
    assert summary.rate("dismissed") == pytest.approx(6.7, abs=0.05)
    assert summary.agreement_rate == 60.0


def test_small_samples_are_flagged_as_not_meaningful() -> None:
    small = report.summarise_triage_rows([triage_row("accepted") for _ in range(29)])
    assert "not meaningful" in report.render_triage(small)

    large = report.summarise_triage_rows([triage_row("accepted") for _ in range(31)])
    assert "not meaningful" not in report.render_triage(large)


def test_the_small_sample_note_names_the_threshold_and_n() -> None:
    summary = report.summarise_triage_rows([triage_row("accepted") for _ in range(12)])
    rendered = report.render_triage(summary)
    assert "12" in rendered
    assert "30" in rendered


def test_no_decisions_yet_says_so_instead_of_dividing_by_zero() -> None:
    summary = report.summarise_triage_rows([])
    assert summary.total == 0
    assert summary.agreement_rate is None
    assert summary.rate("accepted") is None
    rendered = report.render_triage(summary)
    assert "no suggestions" in rendered.lower()


# ---------------------------------------------------------------- the CLI


@pytest.mark.asyncio
async def test_report_renders_every_section(env, monkeypatch, capsys) -> None:
    session = FakeSession(
        tables=ALL_TABLES,
        call_rows=[
            call_row("complaint_triage", "ok", None, 120),
            call_row("complaint_triage", "rejected_budget", "daily_cap", None),
        ],
        triage_rows=[triage_row("accepted"), triage_row("overridden")],
    )

    exit_code = await run(session, "--estate-id", "7", "--days", "14")
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "AI calls" in out
    assert "complaint_triage" in out
    assert "rejected_budget" in out
    assert "daily_cap" in out
    assert "Triage" in out
    assert "accepted" in out and "overridden" in out
    assert "#7" in out


@pytest.mark.asyncio
async def test_target_database_is_printed_without_the_password(env, monkeypatch, capsys) -> None:
    session = FakeSession(tables=ALL_TABLES)

    await run(session, "--estate-id", "7")
    out = capsys.readouterr().out

    assert "localhost:5432/valora_pilot" in out
    assert "s3cret" not in out
    assert "pilot_user" not in out


@pytest.mark.asyncio
async def test_estate_id_is_required(env, capsys) -> None:
    factory = FakeSessionFactory(FakeSession(tables=ALL_TABLES))

    exit_code = await report.main([], session_factory=factory)

    assert exit_code == 2
    assert factory.opened == 0, "argparse must fail before any connection is opened"


@pytest.mark.asyncio
async def test_missing_ledger_table_is_skipped_with_a_clear_message(
    env, monkeypatch, capsys
) -> None:
    session = FakeSession(tables=(), call_rows=[call_row("x", "ok", None, 5)])

    exit_code = await run(session, "--estate-id", "7")
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "ai_call_events" in out
    assert "skipped" in out.lower()
    assert "migration" in out.lower()


@pytest.mark.asyncio
async def test_missing_suggestion_table_is_skipped_with_a_clear_message(
    env, monkeypatch, capsys
) -> None:
    session = FakeSession(tables=("ai_call_events",))

    exit_code = await run(session, "--estate-id", "7")
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "complaint_ai_suggestions" in out
    assert "skipped" in out.lower()


@pytest.mark.asyncio
async def test_health_brief_sections_are_skipped_until_ai4(env, monkeypatch, capsys) -> None:
    session = FakeSession(tables=ALL_TABLES)

    await run(session, "--estate-id", "7")
    out = capsys.readouterr().out

    assert "Brief" in out
    assert "AI-4" in out
    assert "not available" in out.lower()


@pytest.mark.asyncio
async def test_report_is_read_only(env, monkeypatch, capsys) -> None:
    session = FakeSession(
        tables=ALL_TABLES,
        call_rows=[call_row("complaint_triage", "ok", None, 120)],
        triage_rows=[triage_row("accepted")],
    )

    await run(session, "--estate-id", "7")
    capsys.readouterr()

    assert session.writes == 0
    assert session.commits == 0
    assert session.statements, "the report should have queried the ledger"
    for sql in session.statements:
        assert sql.lower().startswith("select"), sql


def test_every_sql_statement_the_module_sends_is_a_select() -> None:
    statements = report.read_only_statements()
    assert statements, "expected at least one statement"
    for sql in statements:
        assert sql.strip().lower().startswith("select"), sql


def test_no_statement_reads_prompt_response_or_resident_text() -> None:
    forbidden = ("prompt", "response", "description", "text", "raw", "payload", "body")
    for sql in report.read_only_statements():
        lowered = sql.lower()
        for word in forbidden:
            assert word not in lowered, f"{word!r} appears in: {sql}"


@pytest.mark.asyncio
async def test_the_days_window_is_a_bound_parameter(env, monkeypatch, capsys) -> None:
    session = FakeSession(tables=ALL_TABLES)

    await run(session, "--estate-id", "9", "--days", "45")
    capsys.readouterr()

    ledger_params = [
        params
        for sql, params in zip(session.statements, session.params)
        if "from ai_call_events" in sql.lower()
    ]
    assert ledger_params and ledger_params[0]["estate_id"] == 9
    assert ledger_params[0]["since"] <= NOW - dt.timedelta(days=44)
    assert "45" not in " ".join(session.statements)


@pytest.mark.asyncio
async def test_an_empty_ledger_reports_zero_calls(env, monkeypatch, capsys) -> None:
    session = FakeSession(tables=ALL_TABLES)

    exit_code = await run(session, "--estate-id", "7")
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "0" in out
    assert "#7" in out


def test_days_must_be_positive() -> None:
    with pytest.raises(SystemExit):
        report.build_parser().parse_args(["--estate-id", "1", "--days", "0"])


def test_redact_database_url_hides_credentials() -> None:
    redacted = report.redact_database_url(
        "postgresql+asyncpg://user:pw@db.example.com:5432/valora_pilot"
    )
    assert redacted == "db.example.com:5432/valora_pilot"
    assert "pw" not in redacted.split("/")[0]
