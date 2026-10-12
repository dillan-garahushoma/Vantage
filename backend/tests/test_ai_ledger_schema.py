"""Schema, repository and migration checks for the AI call ledger (BATCH AI-2).

These run without a database: the model is inspected directly, the repository's
count query is compiled, and the migration is rendered to offline SQL.
"""

from __future__ import annotations

import inspect
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import CheckConstraint, ForeignKeyConstraint
from sqlalchemy.dialects import postgresql

from app.analytics.models.ai_call_event import AICallEvent
from app.analytics.repositories.ai_call_event_repository import AICallEventRepository
from app.property.models.estate import Estate

BACKEND_DIR = Path(__file__).resolve().parent.parent
REVISION = "e5b8c2f1a4d7"  # the head this batch migrates from

# Column names that must never appear: the ledger stores metadata only.
FORBIDDEN_COLUMN_HINTS = (
    "prompt",
    "response",
    "content",
    "text",
    "message",
    "payload",
    "body",
    "user_id",
    "email",
)


def test_ledger_table_stores_metadata_only() -> None:
    columns = set(AICallEvent.__table__.c.keys())

    assert columns == {
        "event_id",
        "estate_id",
        "feature",
        "provider",
        "model",
        "status",
        "reason",
        "latency_ms",
        "input_chars",
        "created_at",
    }
    for hint in FORBIDDEN_COLUMN_HINTS:
        assert hint not in {name.lower() for name in columns}, hint


def test_ledger_columns_are_required_where_they_must_be() -> None:
    columns = AICallEvent.__table__.c

    for name in ("estate_id", "feature", "provider", "model", "status", "created_at"):
        assert columns[name].nullable is False, name
    for name in ("reason", "latency_ms", "input_chars"):
        assert columns[name].nullable is True, name


def test_ledger_status_is_constrained_to_the_closed_set() -> None:
    checks = [
        constraint
        for constraint in AICallEvent.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    ]
    assert checks, "ai_call_events must constrain status"
    body = " ".join(str(constraint.sqltext) for constraint in checks)
    for status in ("ok", "provider_failed", "rejected_policy", "rejected_budget"):
        assert status in body


def test_ledger_estate_foreign_key_restricts_deletes_and_is_named() -> None:
    fks = [
        constraint
        for constraint in AICallEvent.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]
    assert len(fks) == 1
    fk = fks[0]
    assert fk.name == "fk_ai_call_events_estate_id_estates"
    assert {column.name for column in fk.columns} == {"estate_id"}
    assert fk.ondelete == "RESTRICT"


def test_ledger_has_the_estate_created_at_index() -> None:
    index = [
        idx
        for idx in AICallEvent.__table__.indexes
        if "estate_id" in {column.name for column in idx.columns}
        and "created_at" in {column.name for column in idx.columns}
    ]
    assert len(index) == 1
    assert index[0].name == "ix_ai_call_events_estate_id_created_at"


def test_estate_has_a_non_null_demo_flag_defaulting_to_false() -> None:
    column = Estate.__table__.c.is_demo

    assert column.nullable is False
    assert column.server_default is not None
    assert "false" in str(column.server_default.arg).lower()


# ----------------------------------------------------------------- repository


def test_repository_is_append_only() -> None:
    for forbidden in ("update", "delete", "remove", "save"):
        assert not hasattr(AICallEventRepository, forbidden), forbidden


def test_repository_record_flushes_without_committing() -> None:
    source = inspect.getsource(AICallEventRepository.record)

    # Repositories flush; the owning service commits once (AGENTS.md).
    assert ".flush()" in source
    assert ".commit(" not in source


def test_repository_count_statement_is_estate_scoped_and_windowed() -> None:
    statement = AICallEventRepository.count_statement(
        estate_id=3,
        since=datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc),
        statuses=("ok", "provider_failed"),
    )
    sql = str(
        statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )

    assert "ai_call_events" in sql
    assert "estate_id = 3" in sql
    assert "created_at >=" in sql
    assert "status IN ('ok', 'provider_failed')" in sql


def test_repository_count_statement_ignores_extra_statuses_by_default_order() -> None:
    """Status order must not change the compiled SQL (deterministic sort)."""
    since = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)
    first = AICallEventRepository.count_statement(
        estate_id=1, since=since, statuses=("provider_failed", "ok")
    )
    second = AICallEventRepository.count_statement(
        estate_id=1, since=since, statuses=("ok", "provider_failed")
    )
    assert str(first) == str(second)


def test_repository_record_accepts_only_metadata_keywords() -> None:
    parameters = set(inspect.signature(AICallEventRepository.record).parameters)

    assert parameters == {
        "self",
        "estate_id",
        "feature",
        "provider",
        "model",
        "status",
        "reason",
        "latency_ms",
        "input_chars",
    }


# ------------------------------------------------------------------ migrations


def _offline_sql(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", *args],
        cwd=str(BACKEND_DIR),
        env=dict(os.environ),
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_offline_upgrade_sql_creates_the_demo_flag_and_the_ledger() -> None:
    result = _offline_sql("upgrade", "head", "--sql")

    assert result.returncode == 0, result.stderr
    sql = result.stdout
    assert "ALTER TABLE estates ADD COLUMN is_demo BOOLEAN DEFAULT false NOT NULL" in sql
    assert "CREATE TABLE ai_call_events" in sql
    assert "fk_ai_call_events_estate_id_estates" in sql
    assert "CREATE INDEX ix_ai_call_events_estate_id_created_at" in sql


def test_offline_downgrade_sql_reverses_this_migration() -> None:
    result = _offline_sql("downgrade", f"head:{REVISION}", "--sql")

    assert result.returncode == 0, result.stderr
    sql = result.stdout
    assert "DROP INDEX ix_ai_call_events_estate_id_created_at" in sql
    assert "DROP TABLE ai_call_events" in sql
    assert "DROP COLUMN is_demo" in sql
