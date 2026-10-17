"""BATCH 7B — Living Score snapshots, input aggregation and the calculation service.

Layered the same way as `test_security_incidents.py`:

* **Schema, query-shape, serialisation and policy tests** run everywhere, with no
  database: the model is inspected, repository statements are compiled, and the
  service is driven through recording fakes.
* **Isolation and persistence tests** (`@pytest.mark.integration`) are the only
  place a cross-estate claim is made, because a fake cannot prove tenant
  isolation. They auto-skip when `TEST_DATABASE_URL` is unset and are reported as
  not run.

Written before the implementation, per the batch.
"""
from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Numeric
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex
from sqlalchemy.sql.elements import Grouping, Label
from sqlalchemy.sql.functions import Function

from app.analytics.domain import snapshot_vocabulary as vocab
from app.analytics.engine import (
    COMPONENT_KEYS,
    ENGINE_VERSION,
    EstateScoreInputs,
    calculate_living_score,
    window_bounds,
)
from app.analytics.models.living_score_snapshot import LivingScoreSnapshot
from app.analytics.repositories.living_score_inputs_repository import (
    LivingScoreInputsRepository,
)
from app.analytics.repositories.living_score_snapshot_repository import (
    LivingScoreSnapshotRepository,
)
from app.analytics.services.estate_living_score_service import LivingScoreService
from app.common.enums import UserRole
from app.core.exceptions import ForbiddenException, NotFoundException
from app.identity.services.estate_authorization_service import EstateAuthorizationService

BACKEND_DIR = Path(__file__).resolve().parent.parent
PARENT_REVISION = "a7c1e9d4f6b2"  # the 6B head this batch migrates from
MIGRATION_FILE = (
    BACKEND_DIR / "alembic" / "versions" / "c4d8f1a7b9e3_add_living_score_snapshots.py"
)

AS_OF = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
WINDOW_START, WINDOW_END = window_bounds(AS_OF)
ESTATE = 7

SERVICE_MODULE = "app/analytics/services/estate_living_score_service.py"


# --------------------------------------------------------------------------- #
# Doubles. Query shape and policy only - never isolation.
# --------------------------------------------------------------------------- #
class _Result:
    """A scripted result: whatever ``gather`` asks for, in order."""

    def __init__(self, value) -> None:
        self._value = value

    def scalar_one(self):
        return self._value

    def scalar_one_or_none(self):
        return self._value

    def one(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        return list(self._value or [])

    def first(self):
        return self._value[0] if isinstance(self._value, (list, tuple)) else self._value


class ScriptedSession:
    """Records every statement and replays queued results in order."""

    def __init__(self, *results) -> None:
        self.statements: list = []
        self._queue = list(results)

    async def execute(self, statement):
        self.statements.append(statement)
        return _Result(self._queue.pop(0) if self._queue else 0)

    async def commit(self):
        return None

    async def flush(self):
        return None

    async def refresh(self, instance):
        return None


class RecordingSession:
    """Records statements but knows nothing about their results."""

    def __init__(self, result=0) -> None:
        self.statements: list = []
        self._result = result

    async def execute(self, statement):
        self.statements.append(statement)
        return _Result(self._result)


class FakeIncidentRepo:
    def __init__(self, count: int = 0) -> None:
        self.count = count
        self.calls: list[dict] = []

    async def count_in_window(self, *, estate_id: int, start: datetime, end: datetime) -> int:
        self.calls.append({"estate_id": estate_id, "start": start, "end": end})
        return self.count


class FakeMembershipRepo:
    def __init__(self, memberships: list) -> None:
        self.memberships = memberships

    async def list_for_user_and_estate(self, *, user_id: int, estate_id: int):
        return [m for m in self.memberships if m.user_id == user_id and m.estate_id == estate_id]

    async def get_for_user_and_estate(self, *, user_id: int, estate_id: int):
        matches = await self.list_for_user_and_estate(user_id=user_id, estate_id=estate_id)
        return matches[0] if matches else None


def _membership(user_id: int, estate_id: int, role: str, property_id: int | None = None):
    return SimpleNamespace(
        user_id=user_id, estate_id=estate_id, property_id=property_id, membership_role=role
    )


def _auth_service(memberships: list) -> EstateAuthorizationService:
    service = EstateAuthorizationService.__new__(EstateAuthorizationService)
    service._memberships = FakeMembershipRepo(memberships)
    return service


def _admin(estate_id: int = ESTATE, user_id: int = 22):
    return SimpleNamespace(user_id=user_id, role=UserRole.hoa_admin.value)


def _resident(estate_id: int = ESTATE, user_id: int = 21):
    return SimpleNamespace(user_id=user_id, role=UserRole.resident.value)


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0
        self.flushes = 0

    async def commit(self) -> None:
        self.commits += 1

    async def flush(self) -> None:
        self.flushes += 1

    async def refresh(self, instance) -> None:
        return None


class FakeSnapshotRepo:
    def __init__(self, *, items: list | None = None, total: int = 0, latest=None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.added: list[dict] = []
        self._items = items or []
        self._total = total
        self._latest = latest

    async def add(self, **kwargs):
        self.calls.append(("add", kwargs))
        self.added.append(kwargs)
        return SimpleNamespace(snapshot_id=1, **kwargs)

    async def latest_for_estate(self, **kwargs):
        self.calls.append(("latest_for_estate", kwargs))
        return self._latest

    async def history(self, **kwargs):
        self.calls.append(("history", kwargs))
        return list(self._items)

    async def count(self, **kwargs):
        self.calls.append(("count", kwargs))
        return self._total


class FakeInputsRepo:
    def __init__(self, inputs: EstateScoreInputs | None = None) -> None:
        self.gather_calls: list[dict] = []
        self._inputs = inputs or _inputs()

    async def gather(self, *, estate_id: int, as_of: datetime) -> EstateScoreInputs:
        self.gather_calls.append({"estate_id": estate_id, "as_of": as_of})
        return self._inputs


def _inputs(**overrides) -> EstateScoreInputs:
    """The 7A normal case: every component measurable, overall 84.45."""
    payload = {
        "as_of": AS_OF,
        "coverage_days": 90,
        "unit_count": 50,
        "complaints_created": 20,
        "resolved_complaints": 5,
        "avg_resolution_days": Decimal("6"),
        "work_orders_in_window": 8,
        "work_orders_completed": 6,
        "rated_count": 10,
        "avg_rating": Decimal("4.5"),
        "provider_rating_count": 5,
        "avg_provider_rating": Decimal("4"),
        "incidents": 3,
    }
    payload.update(overrides)
    return EstateScoreInputs(**payload)


def _sparse_inputs(**overrides) -> EstateScoreInputs:
    """Too little evidence to score: resolution + satisfaction only (0.45)."""
    payload = {
        "as_of": AS_OF,
        "coverage_days": 10,
        "unit_count": 5,
        "complaints_created": 4,
        "resolved_complaints": 3,
        "avg_resolution_days": Decimal("1"),
        "work_orders_in_window": 0,
        "work_orders_completed": 0,
        "rated_count": 3,
        "avg_rating": Decimal("5"),
        "provider_rating_count": 0,
        "avg_provider_rating": None,
        "incidents": 2,
    }
    payload.update(overrides)
    return EstateScoreInputs(**payload)


def _service(
    *,
    snapshots: FakeSnapshotRepo | None = None,
    inputs: FakeInputsRepo | None = None,
    memberships: list | None = None,
    db: FakeDb | None = None,
) -> LivingScoreService:
    service = LivingScoreService.__new__(LivingScoreService)
    service._db = db or FakeDb()
    service._snapshots = snapshots or FakeSnapshotRepo()
    service._inputs = inputs or FakeInputsRepo()
    service._authorization = _auth_service(memberships if memberships is not None else [])
    return service


def _compiled(statement) -> str:
    return str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


def _dt_literal(moment: datetime) -> str:
    """The date-and-time prefix of a bound datetime, without its precision/offset."""
    return moment.strftime("%Y-%m-%d %H:%M:%S")


def _checks(*names: str):
    return [
        constraint
        for constraint in LivingScoreSnapshot.__table__.constraints
        if isinstance(constraint, CheckConstraint)
        and (not names or constraint.name in names)
    ]


# --------------------------------------------------------------------------- #
# 1. Schema contract
# --------------------------------------------------------------------------- #
def test_snapshot_table_name_and_columns_match_the_contract() -> None:
    assert LivingScoreSnapshot.__tablename__ == "living_score_snapshots"
    assert set(LivingScoreSnapshot.__table__.c.keys()) == {
        "snapshot_id",
        "estate_id",
        "engine_version",
        "as_of",
        "window_start",
        "calculated_at",
        "calculated_by",
        "status",
        "overall_score",
        "measured_weight",
        "resolution_score",
        "frequency_score",
        "security_score",
        "satisfaction_score",
        "infrastructure_score",
        "inputs",
        "explanation",
    }


def test_required_columns_are_not_nullable() -> None:
    columns = LivingScoreSnapshot.__table__.c

    for name in (
        "estate_id",
        "engine_version",
        "as_of",
        "window_start",
        "calculated_at",
        "status",
        "measured_weight",
        "inputs",
        "explanation",
    ):
        assert columns[name].nullable is False, name


def test_optional_columns_are_nullable() -> None:
    columns = LivingScoreSnapshot.__table__.c

    # NULL means "still being calculated" / "not attributed" / "insufficient data",
    # never a fabricated zero.
    for name in ("calculated_by", "overall_score", *vocab.COMPONENT_SCORE_COLUMNS):
        assert columns[name].nullable is True, name


def test_numeric_precisions_match_the_contract() -> None:
    columns = LivingScoreSnapshot.__table__.c

    for name in ("overall_score", *vocab.COMPONENT_SCORE_COLUMNS):
        assert isinstance(columns[name].type, Numeric)
        assert (columns[name].type.precision, columns[name].type.scale) == (5, 2), name
    assert (columns["measured_weight"].type.precision, columns["measured_weight"].type.scale) == (4, 2)


def test_text_and_json_columns_match_the_contract() -> None:
    columns = LivingScoreSnapshot.__table__.c

    assert columns["engine_version"].type.length == 20
    assert columns["status"].type.length == 20
    assert columns["inputs"].type.__class__.__name__ == "JSONB"
    assert columns["explanation"].type.__class__.__name__ == "JSONB"


def test_estate_foreign_key_is_named_and_restricts_deletes() -> None:
    fks = [
        constraint
        for constraint in LivingScoreSnapshot.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]
    by_name = {fk.name: fk for fk in fks}

    estate_fk = by_name.get("fk_living_score_snapshots_estate_id_estates")
    assert estate_fk is not None
    assert {column.name for column in estate_fk.columns} == {"estate_id"}
    assert estate_fk.ondelete == "RESTRICT"


def test_calculated_by_foreign_key_is_named_and_set_null() -> None:
    by_name = {
        constraint.name: constraint
        for constraint in LivingScoreSnapshot.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }

    actor_fk = by_name.get("fk_living_score_snapshots_calculated_by_users")
    assert actor_fk is not None
    assert {column.name for column in actor_fk.columns} == {"calculated_by"}
    assert actor_fk.ondelete == "SET NULL"


def test_status_is_constrained_to_the_two_vocabulary_values() -> None:
    checks = _checks("ck_living_score_snapshots_status")

    assert len(checks) == 1
    body = str(checks[0].sqltext)
    assert "scored" in body
    assert "insufficient_data" in body
    assert set(vocab.SNAPSHOT_STATUSES) == {"scored", "insufficient_data"}


def test_every_score_column_is_bounded_to_zero_and_one_hundred() -> None:
    checks = _checks("ck_living_score_snapshots_scores_bounded")

    assert len(checks) == 1
    body = str(checks[0].sqltext)
    for name in ("overall_score", *vocab.COMPONENT_SCORE_COLUMNS):
        assert name in body, name
    assert "100" in body
    assert "0" in body
    # A component with insufficient data is NULL, which must satisfy the bound.
    assert "IS NULL" in body


def test_status_and_overall_score_agree_by_constraint() -> None:
    checks = _checks("ck_living_score_snapshots_status_matches_overall")

    assert len(checks) == 1
    body = str(checks[0].sqltext)
    assert "(status = 'scored') = (overall_score IS NOT NULL)" in body


def test_the_estate_as_of_index_is_descending() -> None:
    indexes = [
        index
        for index in LivingScoreSnapshot.__table__.indexes
        if index.name == "ix_living_score_snapshots_estate_id_as_of"
    ]

    assert len(indexes) == 1
    ddl = str(CreateIndex(indexes[0]).compile(dialect=postgresql.dialect()))
    assert "living_score_snapshots (estate_id, as_of DESC)" in ddl


def test_the_model_is_registered_in_the_alembic_registry() -> None:
    from app.db import database

    assert hasattr(database, "LivingScoreSnapshot")
    assert "living_score_snapshots" in database.Base.metadata.tables


# --------------------------------------------------------------------------- #
# 2. Migration: offline SQL both ways
# --------------------------------------------------------------------------- #
def _offline_sql(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/valora_test")
    env.setdefault("SECRET_KEY", "test-secret-not-for-production")
    return subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", *args],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_migration_file_exists_and_revises_the_6b_head() -> None:
    source = MIGRATION_FILE.read_text(encoding="utf-8")

    assert MIGRATION_FILE.exists()
    assert f'down_revision: Union[str, Sequence[str], None] = "{PARENT_REVISION}"' in source


def test_offline_upgrade_sql_creates_the_snapshot_table() -> None:
    result = _offline_sql("upgrade", "head", "--sql")

    assert result.returncode == 0, result.stderr
    sql = result.stdout
    assert "CREATE TABLE living_score_snapshots" in sql
    assert "fk_living_score_snapshots_estate_id_estates" in sql
    assert "fk_living_score_snapshots_calculated_by_users" in sql
    assert "ck_living_score_snapshots_status" in sql
    assert "ck_living_score_snapshots_scores_bounded" in sql
    assert "ck_living_score_snapshots_status_matches_overall" in sql
    assert "CREATE INDEX ix_living_score_snapshots_estate_id_as_of" in sql
    assert "inputs JSONB NOT NULL" in sql
    assert "explanation JSONB NOT NULL" in sql


def test_offline_downgrade_sql_reverses_this_migration() -> None:
    result = _offline_sql("downgrade", f"head:{PARENT_REVISION}", "--sql")

    assert result.returncode == 0, result.stderr
    sql = result.stdout
    assert "DROP INDEX ix_living_score_snapshots_estate_id_as_of" in sql
    assert "DROP TABLE living_score_snapshots" in sql


# --------------------------------------------------------------------------- #
# 3. Snapshot repository: append-only, always estate-scoped
# --------------------------------------------------------------------------- #
def test_snapshot_repository_is_append_only() -> None:
    for forbidden in ("update", "delete", "remove", "save", "upsert"):
        assert not hasattr(LivingScoreSnapshotRepository, forbidden), forbidden

    public = {
        name
        for name, _ in inspect.getmembers(LivingScoreSnapshotRepository, inspect.isfunction)
        if not name.startswith("_")
    }
    assert public == {
        "add",
        "latest_for_estate",
        "history",
        "count",
        "latest_statement",
        "history_statement",
        "count_statement",
        # BATCH AI-4 added the read-only comparison lookup the health brief uses
        # to find the snapshots 30 and 90 days earlier. Still no write path.
        "latest_on_or_before",
        "latest_on_or_before_statement",
    }


def test_repository_module_never_builds_an_update_or_delete() -> None:
    import app.analytics.repositories.living_score_snapshot_repository as module

    source = inspect.getsource(module)
    for forbidden in ("sa.update", "sqlalchemy.update", "from sqlalchemy import delete", "delete("):
        assert forbidden not in source, forbidden


def test_snapshot_add_flushes_without_committing() -> None:
    source = inspect.getsource(LivingScoreSnapshotRepository.add)

    assert ".flush()" in source
    assert ".commit(" not in source


@pytest.mark.asyncio
async def test_latest_statement_is_estate_scoped_and_newest_first() -> None:
    session = RecordingSession()
    await LivingScoreSnapshotRepository(session).latest_for_estate(estate_id=ESTATE)

    sql = _compiled(session.statements[0])
    assert f"estate_id = {ESTATE}" in sql
    assert "ORDER BY living_score_snapshots.as_of DESC" in sql
    assert "LIMIT 1" in sql


@pytest.mark.asyncio
async def test_history_statement_is_newest_first_and_paginated() -> None:
    session = RecordingSession(result=[])
    await LivingScoreSnapshotRepository(session).history(estate_id=ESTATE, offset=20, limit=10)

    sql = _compiled(session.statements[0])
    assert f"estate_id = {ESTATE}" in sql
    assert "ORDER BY living_score_snapshots.as_of DESC" in sql
    assert "snapshot_id DESC" in sql
    assert "LIMIT 10 OFFSET 20" in sql


@pytest.mark.asyncio
async def test_count_statement_is_estate_scoped() -> None:
    session = RecordingSession()
    await LivingScoreSnapshotRepository(session).count(estate_id=ESTATE)

    sql = _compiled(session.statements[0])
    assert "count(*) AS count_1" in sql
    assert "FROM living_score_snapshots" in sql
    assert f"estate_id = {ESTATE}" in sql


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda: LivingScoreSnapshotRepository.latest_statement(estate_id=ESTATE), id="latest"),
        pytest.param(
            lambda: LivingScoreSnapshotRepository.history_statement(
                estate_id=ESTATE, offset=0, limit=20
            ),
            id="history",
        ),
        pytest.param(lambda: LivingScoreSnapshotRepository.count_statement(estate_id=ESTATE), id="count"),
    ],
)
def test_no_snapshot_statement_is_unscoped(build) -> None:
    sql = _compiled(build())

    assert "living_score_snapshots" in sql
    assert f"estate_id = {ESTATE}" in sql


# --------------------------------------------------------------------------- #
# 4. Inputs repository: every aggregate filters estate_id AND the window
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "build",
    [
        # unit_count is deliberately excluded: it is the one input without a window
        # (an estate's size is not a windowed fact) and is covered on its own.
        pytest.param(
            lambda repo: repo.complaints_created_statement(
                estate_id=ESTATE, start=WINDOW_START, end=WINDOW_END
            ),
            id="complaints_created",
        ),
        pytest.param(
            lambda repo: repo.resolution_statement(
                estate_id=ESTATE, start=WINDOW_START, end=WINDOW_END
            ),
            id="resolution",
        ),
        pytest.param(
            lambda repo: repo.work_orders_statement(
                estate_id=ESTATE, start=WINDOW_START, end=WINDOW_END
            ),
            id="work_orders",
        ),
        pytest.param(
            lambda repo: repo.ratings_statement(
                estate_id=ESTATE, start=WINDOW_START, end=WINDOW_END
            ),
            id="ratings",
        ),
        pytest.param(
            lambda repo: repo.provider_ratings_statement(
                estate_id=ESTATE, start=WINDOW_START, end=WINDOW_END
            ),
            id="provider_ratings",
        ),
    ],
)
def test_every_windowed_aggregate_filters_by_estate_and_both_window_ends(build) -> None:
    sql = _compiled(build(LivingScoreInputsRepository))

    assert f"estate_id = {ESTATE}" in sql
    assert _dt_literal(WINDOW_START) in sql
    assert _dt_literal(WINDOW_END) in sql


def test_unit_count_is_the_only_aggregate_without_a_window() -> None:
    sql = _compiled(LivingScoreInputsRepository.unit_count_statement(estate_id=ESTATE))

    assert "count(*) AS count_1" in sql
    assert "FROM properties" in sql
    assert f"estate_id = {ESTATE}" in sql
    assert "created_at" not in sql


def test_unit_count_excludes_units_of_other_estates() -> None:
    """The only filter is the estate, so a second estate's units cannot leak in."""
    sql = _compiled(LivingScoreInputsRepository.unit_count_statement(estate_id=ESTATE))

    assert sql.count("WHERE") == 1


def test_complaints_created_window_is_inclusive_at_both_ends() -> None:
    sql = _compiled(
        LivingScoreInputsRepository.complaints_created_statement(
            estate_id=ESTATE, start=WINDOW_START, end=WINDOW_END
        )
    )

    assert "complaints.created_at >=" in sql
    assert "complaints.created_at <=" in sql


def test_resolution_uses_resolved_rated_and_closed_within_the_window() -> None:
    sql = _compiled(
        LivingScoreInputsRepository.resolution_statement(
            estate_id=ESTATE, start=WINDOW_START, end=WINDOW_END
        )
    )

    assert "complaints.status IN ('closed', 'rated', 'resolved')" in sql
    assert "complaints.resolved_at >=" in sql
    assert "complaints.resolved_at <=" in sql
    assert f"complaints.estate_id = {ESTATE}" in sql


def test_work_orders_aggregate_counts_total_and_completed() -> None:
    sql = _compiled(
        LivingScoreInputsRepository.work_orders_statement(
            estate_id=ESTATE, start=WINDOW_START, end=WINDOW_END
        )
    )

    assert "FROM maintenance_work_orders" in sql
    assert "assigned_at >=" in sql
    assert "assigned_at <=" in sql
    assert f"maintenance_work_orders.estate_id = {ESTATE}" in sql
    assert "count(CASE WHEN (maintenance_work_orders.status = 'completed')" in sql


def test_ratings_need_a_completed_work_order_with_a_resident_rating() -> None:
    sql = _compiled(
        LivingScoreInputsRepository.ratings_statement(
            estate_id=ESTATE, start=WINDOW_START, end=WINDOW_END
        )
    )

    assert "maintenance_work_orders.resident_rating IS NOT NULL" in sql
    assert "maintenance_work_orders.status = 'completed'" in sql
    assert "maintenance_work_orders.resolved_at >=" in sql
    assert "count(maintenance_work_orders.resident_rating)" in sql


def test_provider_ratings_deduplicate_providers_within_the_window() -> None:
    sql = _compiled(
        LivingScoreInputsRepository.provider_ratings_statement(
            estate_id=ESTATE, start=WINDOW_START, end=WINDOW_END
        )
    )

    assert "DISTINCT maintenance_work_orders.provider_id" in sql
    assert "JOIN service_providers" in sql
    assert "service_providers.avg_rating IS NOT NULL" in sql
    assert f"maintenance_work_orders.estate_id = {ESTATE}" in sql


def test_coverage_reads_the_estate_created_at_by_primary_key() -> None:
    sql = _compiled(LivingScoreInputsRepository.estate_created_at_statement(estate_id=ESTATE))

    assert "estates.created_at" in sql
    assert f"estates.estate_id = {ESTATE}" in sql


def test_no_aggregate_loads_orm_rows() -> None:
    """Aggregates, not rows: nothing here can hydrate a mapped object (no N+1)."""
    aggregates = [
        LivingScoreInputsRepository.unit_count_statement(estate_id=ESTATE),
        LivingScoreInputsRepository.complaints_created_statement(
            estate_id=ESTATE, start=WINDOW_START, end=WINDOW_END
        ),
        LivingScoreInputsRepository.resolution_statement(
            estate_id=ESTATE, start=WINDOW_START, end=WINDOW_END
        ),
        LivingScoreInputsRepository.work_orders_statement(
            estate_id=ESTATE, start=WINDOW_START, end=WINDOW_END
        ),
        LivingScoreInputsRepository.ratings_statement(
            estate_id=ESTATE, start=WINDOW_START, end=WINDOW_END
        ),
        LivingScoreInputsRepository.provider_ratings_statement(
            estate_id=ESTATE, start=WINDOW_START, end=WINDOW_END
        ),
    ]

    for statement in aggregates:
        # Only aggregates (and their labels) are selected - never a mapped column -
        # so there is nothing to hydrate and no per-row follow-up query.
        for column in statement.selected_columns:
            assert isinstance(column, (Function, Label, Grouping)), column
        sql = _compiled(statement)
        for table in ("complaints", "properties", "maintenance_work_orders"):
            assert f"SELECT {table}." not in sql, sql

    coverage = LivingScoreInputsRepository.estate_created_at_statement(estate_id=ESTATE)
    assert len(list(coverage.selected_columns)) == 1


# --------------------------------------------------------------------------- #
# 5. gather(): the engine window, the incidents boundary, the clamped coverage
# --------------------------------------------------------------------------- #
def _gather_session(*, created_at: datetime, incidents: int = 3) -> tuple[ScriptedSession, FakeIncidentRepo]:
    session = ScriptedSession(
        created_at,  # estates.created_at
        50,  # unit_count
        20,  # complaints created
        (5, Decimal("518400")),  # resolved count, average seconds -> 6 days
        (8, 6),  # work orders total, completed
        (10, Decimal("4.5")),  # rated count, average rating
        (5, Decimal("4")),  # provider count, average provider rating
    )
    return session, FakeIncidentRepo(incidents)


@pytest.mark.asyncio
async def test_gather_uses_the_engine_window_bounds() -> None:
    session, incidents = _gather_session(created_at=AS_OF - timedelta(days=200))
    repo = LivingScoreInputsRepository(session, incidents=incidents)

    await repo.gather(estate_id=ESTATE, as_of=AS_OF)

    # Statement 0 is the estate lookup and statement 1 is the unit count; every
    # statement after those is windowed.
    assert len(session.statements) == 7
    assert _dt_literal(WINDOW_START) not in _compiled(session.statements[1])
    for statement in session.statements[2:]:
        sql = _compiled(statement)
        assert _dt_literal(WINDOW_START) in sql
        assert _dt_literal(WINDOW_END) in sql


@pytest.mark.asyncio
async def test_gather_asks_security_incidents_for_an_inclusive_window() -> None:
    """6B's helper is half-open; the engine's window is inclusive at both ends."""
    session, incidents = _gather_session(created_at=AS_OF - timedelta(days=200))
    repo = LivingScoreInputsRepository(session, incidents=incidents)

    await repo.gather(estate_id=ESTATE, as_of=AS_OF)

    assert len(incidents.calls) == 1
    call = incidents.calls[0]
    assert call["estate_id"] == ESTATE
    assert call["start"] == WINDOW_START
    assert call["end"] == WINDOW_END + timedelta(microseconds=1)


@pytest.mark.asyncio
async def test_gather_builds_engine_inputs_with_decimal_averages() -> None:
    session, incidents = _gather_session(created_at=AS_OF - timedelta(days=200), incidents=3)
    repo = LivingScoreInputsRepository(session, incidents=incidents)

    inputs = await repo.gather(estate_id=ESTATE, as_of=AS_OF)

    assert isinstance(inputs, EstateScoreInputs)
    assert inputs.as_of == AS_OF
    assert inputs.coverage_days == 90
    assert inputs.unit_count == 50
    assert inputs.complaints_created == 20
    assert inputs.resolved_complaints == 5
    assert inputs.avg_resolution_days == Decimal("6")
    assert inputs.work_orders_in_window == 8
    assert inputs.work_orders_completed == 6
    assert inputs.rated_count == 10
    assert inputs.avg_rating == Decimal("4.5")
    assert inputs.provider_rating_count == 5
    assert inputs.avg_provider_rating == Decimal("4")
    assert inputs.incidents == 3
    for value in (inputs.avg_resolution_days, inputs.avg_rating, inputs.avg_provider_rating):
        assert isinstance(value, Decimal)


@pytest.mark.asyncio
async def test_gather_passes_no_average_through_when_nothing_was_resolved() -> None:
    session = ScriptedSession(
        AS_OF - timedelta(days=200),
        50,
        4,  # complaints created
        (0, None),  # nothing resolved: no average, no exception
        (0, 0),
        (0, None),
        (0, None),
    )
    repo = LivingScoreInputsRepository(session, incidents=FakeIncidentRepo(0))

    inputs = await repo.gather(estate_id=ESTATE, as_of=AS_OF)

    assert inputs.resolved_complaints == 0
    assert inputs.avg_resolution_days is None
    assert inputs.avg_rating is None
    assert inputs.provider_rating_count == 0
    assert inputs.avg_provider_rating is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "age,expected",
    [
        (timedelta(days=400), 90),
        (timedelta(days=91), 90),
        (timedelta(days=90), 90),
        (timedelta(days=45, hours=3), 45),
        (timedelta(hours=5), 0),
        (timedelta(seconds=1), 0),
    ],
)
async def test_gather_clamps_coverage_days_to_zero_through_ninety(
    age: timedelta, expected: int
) -> None:
    session, incidents = _gather_session(created_at=AS_OF - age)
    repo = LivingScoreInputsRepository(session, incidents=incidents)

    assert (await repo.gather(estate_id=ESTATE, as_of=AS_OF)).coverage_days == expected


@pytest.mark.asyncio
async def test_gather_raises_not_found_for_an_unknown_estate() -> None:
    session = ScriptedSession(None)
    repo = LivingScoreInputsRepository(session, incidents=FakeIncidentRepo(0))

    with pytest.raises(NotFoundException):
        await repo.gather(estate_id=ESTATE, as_of=AS_OF)


@pytest.mark.asyncio
async def test_gather_issues_a_fixed_number_of_statements() -> None:
    """Seven statements no matter how much data the estate has: no per-row queries."""
    session, incidents = _gather_session(created_at=AS_OF - timedelta(days=200))
    repo = LivingScoreInputsRepository(session, incidents=incidents)

    await repo.gather(estate_id=ESTATE, as_of=AS_OF)

    assert len(session.statements) == 7


# --------------------------------------------------------------------------- #
# 6. The service: who may calculate, what is stored
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_a_resident_cannot_calculate_a_snapshot() -> None:
    service = _service(memberships=[_membership(21, ESTATE, UserRole.resident.value, 1)])

    with pytest.raises(ForbiddenException):
        await service.calculate_and_snapshot(estate_id=ESTATE, actor=_resident())


@pytest.mark.asyncio
async def test_a_global_admin_without_membership_cannot_calculate() -> None:
    """hoa_admin globally is not enough: the estate membership must match too."""
    service = _service(memberships=[_membership(22, 999, UserRole.hoa_admin.value)])

    with pytest.raises(ForbiddenException):
        await service.calculate_and_snapshot(estate_id=ESTATE, actor=_admin())


@pytest.mark.asyncio
async def test_an_estate_admin_persists_exactly_one_snapshot_with_the_engine_version() -> None:
    snapshots = FakeSnapshotRepo()
    service = _service(
        snapshots=snapshots,
        memberships=[_membership(22, ESTATE, UserRole.hoa_admin.value)],
    )

    await service.calculate_and_snapshot(estate_id=ESTATE, actor=_admin())

    assert [name for name, _ in snapshots.calls] == ["add"]
    payload = snapshots.added[0]
    assert payload["estate_id"] == ESTATE
    assert payload["engine_version"] == ENGINE_VERSION
    assert payload["engine_version"] == "1.0.0"
    assert payload["status"] == "scored"
    assert payload["calculated_by"] == 22
    assert payload["as_of"] == AS_OF
    assert payload["window_start"] == WINDOW_START
    assert payload["overall_score"] == Decimal("84.45")
    assert payload["measured_weight"] == Decimal("1.00")


@pytest.mark.asyncio
async def test_the_stored_component_columns_come_from_the_engine() -> None:
    snapshots = FakeSnapshotRepo()
    service = _service(
        snapshots=snapshots, memberships=[_membership(22, ESTATE, UserRole.hoa_admin.value)]
    )

    await service.calculate_and_snapshot(estate_id=ESTATE, actor=_admin())

    expected = calculate_living_score(_inputs())
    payload = snapshots.added[0]
    assert payload["resolution_score"] == Decimal("82.76")
    assert payload["frequency_score"] == Decimal("92.00")
    assert payload["security_score"] == Decimal("80.00")
    assert payload["satisfaction_score"] == Decimal("87.50")
    assert payload["infrastructure_score"] == Decimal("75.00")
    assert payload["overall_score"] == expected.overall_score


@pytest.mark.asyncio
async def test_the_stored_inputs_capture_the_aggregates() -> None:
    snapshots = FakeSnapshotRepo()
    service = _service(
        snapshots=snapshots, memberships=[_membership(22, ESTATE, UserRole.hoa_admin.value)]
    )

    await service.calculate_and_snapshot(estate_id=ESTATE, actor=_admin())

    inputs = snapshots.added[0]["inputs"]
    # JSON-safe: datetimes as ISO strings, Decimals as strings so nothing is lost.
    assert inputs["as_of"] == AS_OF.isoformat()
    assert inputs["coverage_days"] == 90
    assert inputs["unit_count"] == 50
    assert inputs["complaints_created"] == 20
    assert inputs["resolved_complaints"] == 5
    assert inputs["avg_resolution_days"] == "6"
    assert inputs["work_orders_in_window"] == 8
    assert inputs["work_orders_completed"] == 6
    assert inputs["rated_count"] == 10
    assert inputs["avg_rating"] == "4.5"
    assert inputs["provider_rating_count"] == 5
    assert inputs["avg_provider_rating"] == "4"
    assert inputs["incidents"] == 3
    json.dumps(inputs)


@pytest.mark.asyncio
async def test_the_stored_explanation_carries_every_component_and_the_drivers() -> None:
    snapshots = FakeSnapshotRepo()
    service = _service(
        snapshots=snapshots, memberships=[_membership(22, ESTATE, UserRole.hoa_admin.value)]
    )

    await service.calculate_and_snapshot(estate_id=ESTATE, actor=_admin())

    explanation = snapshots.added[0]["explanation"]
    assert [c["key"] for c in explanation["components"]] == list(COMPONENT_KEYS)
    assert [c["key"] for c in explanation["drivers"]] == [
        "resolution",
        "security",
        "infrastructure",
        "frequency",
        "satisfaction",
    ]
    resolution = explanation["components"][0]
    for field in (
        "key",
        "weight",
        "status",
        "score",
        "raw_inputs",
        "benchmark",
        "contribution",
        "lost_points",
        "explanation",
        "recommendation",
    ):
        assert field in resolution, field
    # Nothing is below the 70 threshold in this healthy case, so no advice is given.
    assert resolution["recommendation"] is None
    assert [c["recommendation"] for c in explanation["components"]] == [None] * 5
    assert explanation["engine_version"] == "1.0.0"
    assert explanation["measured_weight"] == "1.00"
    assert explanation["status"] == "scored"
    json.dumps(explanation)


@pytest.mark.asyncio
async def test_a_weak_component_carries_its_static_recommendation() -> None:
    snapshots = FakeSnapshotRepo()
    service = _service(
        snapshots=snapshots,
        inputs=FakeInputsRepo(_inputs(incidents=12)),
        memberships=[_membership(22, ESTATE, UserRole.hoa_admin.value)],
    )

    await service.calculate_and_snapshot(estate_id=ESTATE, actor=_admin(), as_of=AS_OF)

    explanation = snapshots.added[0]["explanation"]
    security = next(c for c in explanation["components"] if c["key"] == "security")
    assert security["score"] == "20.00"
    assert security["recommendation"]
    # A weak component becomes the leading driver of the score.
    assert explanation["drivers"][0]["key"] == "security"


@pytest.mark.asyncio
async def test_the_same_data_and_as_of_give_identical_numbers() -> None:
    first, second = FakeSnapshotRepo(), FakeSnapshotRepo()
    memberships = [_membership(22, ESTATE, UserRole.hoa_admin.value)]

    await _service(snapshots=first, memberships=memberships).calculate_and_snapshot(
        estate_id=ESTATE, actor=_admin(), as_of=AS_OF
    )
    await _service(snapshots=second, memberships=memberships).calculate_and_snapshot(
        estate_id=ESTATE, actor=_admin(), as_of=AS_OF
    )

    assert first.added[0] == second.added[0]


@pytest.mark.asyncio
async def test_insufficient_data_stores_a_null_overall_and_no_component_scores() -> None:
    snapshots = FakeSnapshotRepo()
    service = _service(
        snapshots=snapshots,
        inputs=FakeInputsRepo(_sparse_inputs()),
        memberships=[_membership(22, ESTATE, UserRole.hoa_admin.value)],
    )

    await service.calculate_and_snapshot(estate_id=ESTATE, actor=_admin())

    payload = snapshots.added[0]
    assert payload["status"] == "insufficient_data"
    assert payload["overall_score"] is None
    # 0.45 of the weight was measurable, below the 0.50 floor (7A decision D3).
    assert payload["measured_weight"] == Decimal("0.45")
    assert payload["resolution_score"] == Decimal("100.00")
    assert payload["satisfaction_score"] == Decimal("100.00")
    # NULL, never a fabricated zero, for the components that had no evidence.
    assert payload["frequency_score"] is None
    assert payload["security_score"] is None
    assert payload["infrastructure_score"] is None


@pytest.mark.asyncio
async def test_as_of_is_read_once(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.analytics.services.estate_living_score_service as module

    calls: list[datetime] = []

    def fake_utcnow() -> datetime:
        calls.append(AS_OF)
        return AS_OF

    monkeypatch.setattr(module, "utcnow", fake_utcnow)
    inputs = FakeInputsRepo()
    snapshots = FakeSnapshotRepo()
    service = _service(
        snapshots=snapshots,
        inputs=inputs,
        memberships=[_membership(22, ESTATE, UserRole.hoa_admin.value)],
    )

    await service.calculate_and_snapshot(estate_id=ESTATE, actor=_admin())

    assert len(calls) == 1
    assert inputs.gather_calls[0]["as_of"] == AS_OF
    assert snapshots.added[0]["as_of"] == AS_OF
    assert snapshots.added[0]["window_start"] == WINDOW_START


@pytest.mark.asyncio
async def test_an_explicit_as_of_does_not_read_the_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.analytics.services.estate_living_score_service as module

    def explode() -> datetime:
        raise AssertionError("as_of was supplied, so the clock must not be read")

    monkeypatch.setattr(module, "utcnow", explode)
    inputs = FakeInputsRepo()
    service = _service(
        inputs=inputs, memberships=[_membership(22, ESTATE, UserRole.hoa_admin.value)]
    )

    await service.calculate_and_snapshot(estate_id=ESTATE, actor=_admin(), as_of=AS_OF)

    assert inputs.gather_calls[0]["as_of"] == AS_OF


@pytest.mark.asyncio
async def test_the_service_commits_and_the_repository_only_flushes() -> None:
    db = FakeDb()
    service = _service(db=db, memberships=[_membership(22, ESTATE, UserRole.hoa_admin.value)])

    await service.calculate_and_snapshot(estate_id=ESTATE, actor=_admin())

    assert db.commits == 1, "a multi-step use case commits once, in the service"
    source = inspect.getsource(LivingScoreSnapshotRepository.add)
    assert ".flush()" in source and ".commit(" not in source


@pytest.mark.asyncio
async def test_an_actor_of_none_is_allowed_for_the_cli_path_only() -> None:
    """The CLI may calculate without an actor; HTTP must never reach that path."""
    inputs = FakeInputsRepo()
    service = _service(inputs=inputs, memberships=[])

    await service.calculate_and_snapshot(estate_id=ESTATE, actor=None)

    assert inputs.gather_calls, "the CLI path must still gather and persist"


def test_no_api_module_reaches_the_calculation_service() -> None:
    """Only the CLI and one thin router may reach the calculation service.

    BATCH 7B asserted the service was not wired to HTTP at all. BATCH 7C wired it
    to exactly one router, and that stays the whole HTTP surface: no other API
    module may name it.
    """
    score_router = "app/analytics/api/living_score.py"
    allowed = {SERVICE_MODULE, score_router, "app/cli.py"}
    offenders = []
    for path in sorted((BACKEND_DIR / "app").rglob("*.py")):
        relative = path.relative_to(BACKEND_DIR).as_posix()
        if relative in allowed:
            continue
        if "LivingScoreService" in path.read_text(encoding="utf-8"):
            offenders.append(relative)

    assert offenders == []
    api_dirs = list((BACKEND_DIR / "app").glob("*/api"))
    for api_dir in api_dirs:
        for path in api_dir.rglob("*.py"):
            relative = path.relative_to(BACKEND_DIR).as_posix()
            if relative == score_router:
                continue
            assert "estate_living_score_service" not in path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# 7. Reads: membership required, never recalculated
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_a_non_member_cannot_read_the_latest_snapshot() -> None:
    service = _service(memberships=[_membership(21, 999, UserRole.resident.value, 1)])

    with pytest.raises(ForbiddenException):
        await service.latest(estate_id=ESTATE, user=_resident())


@pytest.mark.asyncio
async def test_an_estate_member_may_read_the_latest_snapshot() -> None:
    """Reads need membership, not admin rights: a resident of the estate may read."""
    stored = SimpleNamespace(snapshot_id=5)
    snapshots = FakeSnapshotRepo(latest=stored)
    service = _service(
        snapshots=snapshots,
        memberships=[_membership(21, ESTATE, UserRole.resident.value, 1)],
    )

    assert await service.latest(estate_id=ESTATE, user=_resident()) is stored
    assert snapshots.calls == [("latest_for_estate", {"estate_id": ESTATE})]


@pytest.mark.asyncio
async def test_a_non_member_cannot_read_the_history() -> None:
    service = _service(memberships=[])

    with pytest.raises(ForbiddenException):
        await service.history(estate_id=ESTATE, user=_admin(), page=1, size=20)


@pytest.mark.asyncio
async def test_latest_returns_none_when_no_snapshot_exists() -> None:
    snapshots = FakeSnapshotRepo(latest=None)
    service = _service(
        snapshots=snapshots, memberships=[_membership(21, ESTATE, UserRole.resident.value, 1)]
    )

    assert await service.latest(estate_id=ESTATE, user=_resident()) is None


@pytest.mark.asyncio
async def test_history_returns_the_newest_first_page_with_a_total() -> None:
    items = [SimpleNamespace(snapshot_id=n) for n in (3, 2, 1)]
    snapshots = FakeSnapshotRepo(items=items, total=7)
    service = _service(
        snapshots=snapshots, memberships=[_membership(21, ESTATE, UserRole.resident.value, 1)]
    )

    page = await service.history(estate_id=ESTATE, user=_resident(), page=2, size=3)

    assert page.items == items
    assert page.total == 7
    assert ("history", {"estate_id": ESTATE, "offset": 3, "limit": 3}) in snapshots.calls


@pytest.mark.asyncio
async def test_reads_never_recalculate() -> None:
    inputs = FakeInputsRepo()
    snapshots = FakeSnapshotRepo(latest=SimpleNamespace(snapshot_id=1), items=[], total=0)
    service = _service(
        snapshots=snapshots,
        inputs=inputs,
        memberships=[_membership(22, ESTATE, UserRole.hoa_admin.value)],
    )

    await service.latest(estate_id=ESTATE, user=_admin())
    await service.history(estate_id=ESTATE, user=_admin(), page=1, size=20)

    assert inputs.gather_calls == [], "a stored snapshot is never recalculated on read"
    assert [name for name, _ in snapshots.calls] == ["latest_for_estate", "history", "count"]


def test_the_service_does_not_import_the_engine_through_the_database_layer() -> None:
    """The engine stays ignorant of the DB: only the service bridges the two."""
    import app.analytics.services.estate_living_score_service as service_module

    source = inspect.getsource(service_module)
    assert "calculate_living_score" in source
    engine_source = inspect.getsource(
        sys.modules["app.analytics.engine.living_score"]
    )
    for forbidden in ("sqlalchemy", "AsyncSession", "app.db"):
        assert forbidden not in engine_source, forbidden


# --------------------------------------------------------------------------- #
# 8. Integration: real database, real isolation
# --------------------------------------------------------------------------- #
# The two estates are seeded here rather than through ``tests.factories``: that
# helper passes ``hoa_approved`` to ``UserRepository.create``, which does not
# accept it in this tree, so every DB-backed test that uses ``build_two_estate_world``
# errors before it can assert anything (6B's incident isolation test included).
# That is a pre-existing defect in another module; this batch does not depend on it.


async def _seed_world(db):
    """Two estates with real operations, inside and outside the 90-day window."""
    from app.community.models.complaint import Complaint
    from app.community.models.maintenance_work_order import MaintenanceworkOrder
    from app.community.models.security_incident import SecurityIncident
    from app.identity.models.estate_membership import EstateMembership
    from app.identity.models.user import User
    from app.property.models.estate import Estate
    from app.property.models.property import Property
    from app.providers.models.service_provider import ServiceProvider

    now = datetime.now(timezone.utc)
    operates_since = now - timedelta(days=60)  # 60 days of coverage, inside the window

    estate_a = Estate(
        name="7B Zambezi", suburb="Montana", city="Pretoria", province="Gauteng",
        created_at=operates_since,
    )
    estate_b = Estate(
        name="7B Silver Lakes", suburb="Silver Lakes", city="Pretoria", province="Gauteng",
        created_at=operates_since,
    )
    db.add_all([estate_a, estate_b])
    await db.commit()

    admin_a = User(email="7b_admin_a@valora.test", password_hash="x", full_name="Admin A",
                   role=UserRole.hoa_admin.value)
    admin_b = User(email="7b_admin_b@valora.test", password_hash="x", full_name="Admin B",
                   role=UserRole.hoa_admin.value)
    resident_a = User(email="7b_resident_a@valora.test", password_hash="x", full_name="Resident A",
                      role=UserRole.resident.value)
    provider_user = User(email="7b_provider@valora.test", password_hash="x", full_name="Pete",
                         role=UserRole.service_provider.value)
    db.add_all([admin_a, admin_b, resident_a, provider_user])
    await db.commit()

    property_a1 = Property(estate_id=estate_a.estate_id, unit_no="7B-01", complex_name="Zambezi",
                           street_address="1 Zambezi Drive", suburb="Montana")
    property_a2 = Property(estate_id=estate_a.estate_id, unit_no="7B-02", complex_name="Zambezi",
                           street_address="2 Zambezi Drive", suburb="Montana")
    property_b1 = Property(estate_id=estate_b.estate_id, unit_no="7B-11", complex_name="Silver",
                           street_address="11 Fairway Lane", suburb="Silver Lakes")
    db.add_all([property_a1, property_a2, property_b1])
    await db.commit()

    provider_a = ServiceProvider(
        user_id=provider_user.user_id, full_name="Pete Plumbing", trade="plumbing",
        phone="0821234567", email="7b_pete@plumbing.test", avg_rating=Decimal("4.00"),
    )
    db.add(provider_a)
    await db.commit()

    db.add_all(
        [
            EstateMembership(user_id=admin_a.user_id, estate_id=estate_a.estate_id,
                             membership_role=UserRole.hoa_admin.value),
            EstateMembership(user_id=resident_a.user_id, estate_id=estate_a.estate_id,
                             property_id=property_a1.unit_id,
                             membership_role=UserRole.resident.value),
            EstateMembership(user_id=admin_b.user_id, estate_id=estate_b.estate_id,
                             membership_role=UserRole.hoa_admin.value),
        ]
    )
    await db.commit()

    # Estate A: four complaints in the window (three resolved, averaging 4/3 days)
    # and one comfortably before it that must not be counted anywhere.
    def complaint(unit_id, status, raised_days, resolved_days=None):
        return Complaint(
            user_id=resident_a.user_id, estate_id=estate_a.estate_id, unit_id=unit_id,
            category="water", description="A reported problem.", priority="normal",
            status=status, created_at=now - timedelta(days=raised_days),
            resolved_at=None if resolved_days is None else now - timedelta(days=resolved_days),
        )

    c1 = complaint(property_a1.unit_id, "resolved", 40, 39)
    c2 = complaint(property_a1.unit_id, "rated", 30, 28)
    c3 = complaint(property_a2.unit_id, "in_progress", 20)
    c5 = complaint(property_a2.unit_id, "resolved", 10, 9)
    stale = complaint(property_a1.unit_id, "resolved", 200, 199)
    db.add_all([c1, c2, c3, c5, stale])
    await db.commit()

    def work_order(complaint, status, assigned_days, resolved_days=None, rating=None):
        return MaintenanceworkOrder(
            complaint_id=complaint.complaint_id, estate_id=estate_a.estate_id,
            provider_id=provider_a.provider_id, status=status,
            assigned_at=now - timedelta(days=assigned_days),
            resolved_at=None if resolved_days is None else now - timedelta(days=resolved_days),
            resident_rating=rating,
        )

    db.add_all(
        [
            work_order(c1, "completed", 39, 38, 5),
            work_order(c2, "completed", 28, 27, 4),
            work_order(c3, "in_progress", 19),
            work_order(c5, "completed", 9, 8, 5),
        ]
    )
    await db.commit()

    db.add_all(
        [
            SecurityIncident(estate_id=estate_a.estate_id, category="theft", severity="high",
                             status="open", occurred_at=now - timedelta(days=5)),
            SecurityIncident(estate_id=estate_a.estate_id, category="trespass", severity="low",
                             status="resolved", occurred_at=now - timedelta(days=20),
                             resolved_at=now - timedelta(days=19)),
            SecurityIncident(estate_id=estate_a.estate_id, category="vandalism", severity="medium",
                             status="open", occurred_at=now - timedelta(days=200)),
            # Estate B's own activity, which estate A must never see.
            SecurityIncident(estate_id=estate_b.estate_id, category="theft", severity="high",
                             status="open", occurred_at=now - timedelta(days=3)),
        ]
    )
    db.add(
        Complaint(
            user_id=admin_b.user_id, estate_id=estate_b.estate_id, unit_id=property_b1.unit_id,
            category="electrical", description="Lobby light.", priority="normal",
            status="submitted", created_at=now - timedelta(days=7),
        )
    )
    await db.commit()

    return SimpleNamespace(
        as_of=now,
        estate_a=estate_a,
        estate_b=estate_b,
        admin_a=admin_a,
        admin_b=admin_b,
        resident_a=resident_a,
        property_a1=property_a1,
        property_b1=property_b1,
        provider_a=provider_a,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_calculate_and_snapshot_persists_and_reads_back(db_session) -> None:
    world = await _seed_world(db_session)
    service = LivingScoreService(db_session)
    estate_id = world.estate_a.estate_id

    stored = await service.calculate_and_snapshot(
        estate_id=estate_id, actor=world.admin_a, as_of=world.as_of
    )

    assert stored.snapshot_id is not None
    assert stored.engine_version == "1.0.0"
    assert stored.estate_id == estate_id
    assert stored.calculated_by == world.admin_a.user_id
    assert stored.status == "scored"
    assert stored.overall_score is not None
    # The aggregates really came out of PostgreSQL, not out of a fake.
    assert stored.inputs["unit_count"] == 2
    assert stored.inputs["coverage_days"] == 60
    assert stored.inputs["complaints_created"] == 4
    assert stored.inputs["resolved_complaints"] == 3
    assert stored.inputs["work_orders_in_window"] == 4
    assert stored.inputs["work_orders_completed"] == 3
    assert stored.inputs["rated_count"] == 3
    assert stored.inputs["provider_rating_count"] == 1
    assert stored.inputs["incidents"] == 2
    assert stored.explanation["engine_version"] == "1.0.0"
    assert len(stored.explanation["components"]) == 5

    latest = await service.latest(estate_id=estate_id, user=world.resident_a)
    assert latest is not None
    assert latest.snapshot_id == stored.snapshot_id
    assert latest.overall_score == stored.overall_score
    assert latest.status == stored.status

    page = await service.history(estate_id=estate_id, user=world.resident_a, page=1, size=20)
    assert page.total == 1
    assert [s.snapshot_id for s in page.items] == [stored.snapshot_id]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_the_same_window_recalculates_to_the_same_numbers(db_session) -> None:
    """Same data, same as_of, same numbers - through the real database."""
    world = await _seed_world(db_session)
    service = LivingScoreService(db_session)
    estate_id = world.estate_a.estate_id

    inputs = await LivingScoreInputsRepository(db_session).gather(
        estate_id=estate_id, as_of=world.as_of
    )
    expected = calculate_living_score(inputs)
    stored = await service.calculate_and_snapshot(
        estate_id=estate_id, actor=world.admin_a, as_of=world.as_of
    )

    assert stored.overall_score == expected.overall_score
    assert stored.measured_weight == expected.measured_weight
    assert stored.status == expected.status
    for component in expected.components:
        assert getattr(stored, f"{component.key}_score") == component.score, component.key
    # The stored inputs are the aggregates the engine actually consumed.
    assert stored.inputs["avg_resolution_days"] == str(inputs.avg_resolution_days)
    assert stored.inputs["avg_rating"] == str(inputs.avg_rating)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_an_estate_with_too_little_history_stores_a_null_overall(db_session) -> None:
    """Estate B has no resolved complaints, ratings or work orders: 0.45 weight."""
    world = await _seed_world(db_session)
    service = LivingScoreService(db_session)

    stored = await service.calculate_and_snapshot(
        estate_id=world.estate_b.estate_id, actor=world.admin_b, as_of=world.as_of
    )

    assert stored.status == "insufficient_data"
    assert stored.overall_score is None
    assert stored.measured_weight == Decimal("0.45")
    assert stored.resolution_score is None
    assert stored.satisfaction_score is None
    assert stored.infrastructure_score is None
    assert stored.frequency_score == Decimal("80.00")
    assert stored.security_score == Decimal("93.33")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_non_member_and_a_resident_cannot_calculate_in_a_real_database(
    db_session,
) -> None:
    world = await _seed_world(db_session)
    service = LivingScoreService(db_session)

    # A resident of the estate: role alone is not enough.
    with pytest.raises(ForbiddenException):
        await service.calculate_and_snapshot(
            estate_id=world.estate_a.estate_id, actor=world.resident_a
        )
    # An HOA admin of a different estate: global role, wrong tenant.
    with pytest.raises(ForbiddenException):
        await service.calculate_and_snapshot(
            estate_id=world.estate_a.estate_id, actor=world.admin_b
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gather_is_cross_estate_isolated_in_a_real_database(db_session) -> None:
    world = await _seed_world(db_session)
    repo = LivingScoreInputsRepository(db_session)

    a = await repo.gather(estate_id=world.estate_a.estate_id, as_of=world.as_of)
    assert a.unit_count == 2
    assert a.complaints_created == 4
    assert a.resolved_complaints == 3
    assert a.work_orders_in_window == 4
    assert a.work_orders_completed == 3
    assert a.rated_count == 3
    assert a.provider_rating_count == 1
    assert a.incidents == 2
    # 86400/172800/86400 seconds -> a 4/3-day average, from estate A's rows only.
    assert a.avg_resolution_days.quantize(Decimal("0.01")) == Decimal("1.33")
    assert a.avg_rating.quantize(Decimal("0.01")) == Decimal("4.67")
    assert a.avg_provider_rating == Decimal("4.00")

    b = await repo.gather(estate_id=world.estate_b.estate_id, as_of=world.as_of)
    assert b.unit_count == 1
    assert b.complaints_created == 1
    assert b.resolved_complaints == 0
    assert b.work_orders_in_window == 0
    assert b.rated_count == 0
    assert b.provider_rating_count == 0
    assert b.incidents == 1
    assert b.avg_resolution_days is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_legacy_complaint_with_no_estate_belongs_to_no_estate(db_session) -> None:
    """The pre-tenancy rows are excluded by construction, not by filtering them out."""
    from app.community.models.complaint import Complaint

    world = await _seed_world(db_session)
    repo = LivingScoreInputsRepository(db_session)

    db_session.add(
        Complaint(
            user_id=world.resident_a.user_id,
            estate_id=None,  # legacy row that predates estate tenancy
            unit_id=world.property_a1.unit_id,
            category="water",
            description="Legacy row.",
            priority="normal",
            status="resolved",
            created_at=world.as_of - timedelta(days=5),
            resolved_at=world.as_of - timedelta(days=4),
        )
    )
    await db_session.commit()

    a = await repo.gather(estate_id=world.estate_a.estate_id, as_of=world.as_of)
    b = await repo.gather(estate_id=world.estate_b.estate_id, as_of=world.as_of)

    assert a.complaints_created == 4
    assert a.resolved_complaints == 3
    assert b.complaints_created == 1
    assert b.resolved_complaints == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_snapshot_history_is_newest_first_and_estate_scoped(db_session) -> None:
    world = await _seed_world(db_session)
    service = LivingScoreService(db_session)
    estate_a = world.estate_a.estate_id

    older = await service.calculate_and_snapshot(
        estate_id=estate_a, actor=world.admin_a, as_of=world.as_of - timedelta(days=30)
    )
    newer = await service.calculate_and_snapshot(
        estate_id=estate_a, actor=world.admin_a, as_of=world.as_of
    )
    await service.calculate_and_snapshot(
        estate_id=world.estate_b.estate_id, actor=world.admin_b, as_of=world.as_of
    )

    page = await service.history(estate_id=estate_a, user=world.resident_a, page=1, size=20)

    assert page.total == 2
    assert [s.snapshot_id for s in page.items] == [newer.snapshot_id, older.snapshot_id]
    assert all(s.estate_id == estate_a for s in page.items)
    # The two windows are remembered exactly as they were calculated.
    assert [s.as_of for s in page.items] == [world.as_of, world.as_of - timedelta(days=30)]
    assert page.items[1].window_start == world.as_of - timedelta(days=120)

    latest = await service.latest(estate_id=estate_a, user=world.resident_a)
    assert latest is not None and latest.snapshot_id == newer.snapshot_id
    # Paging is real, not a single page pretending to be complete.
    first = await service.history(estate_id=estate_a, user=world.resident_a, page=1, size=1)
    assert first.total == 2 and len(first.items) == 1
    assert first.items[0].snapshot_id == newer.snapshot_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_no_update_or_delete_is_issued_against_the_snapshot_table(db_session) -> None:
    from sqlalchemy import event

    world = await _seed_world(db_session)
    service = LivingScoreService(db_session)
    estate_a = world.estate_a.estate_id
    seen: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany):
        seen.append(statement)

    sync_engine = db_session.bind.sync_engine
    event.listen(sync_engine, "before_cursor_execute", record)
    try:
        await service.calculate_and_snapshot(
            estate_id=estate_a, actor=world.admin_a, as_of=world.as_of
        )
        await service.latest(estate_id=estate_a, user=world.resident_a)
        await service.history(estate_id=estate_a, user=world.resident_a, page=1, size=20)
    finally:
        event.remove(sync_engine, "before_cursor_execute", record)

    snapshot_sql = [s for s in seen if "living_score_snapshots" in s]
    assert snapshot_sql, "the snapshot table must have been touched"
    for statement in snapshot_sql:
        head = statement.strip().split()[0].upper()
        assert head in {"SELECT", "INSERT"}, statement
    assert not [s for s in seen if "DELETE FROM living_score_snapshots" in s]
    assert not [s for s in seen if "UPDATE living_score_snapshots" in s]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_the_migrated_schema_itself_refuses_a_contradictory_snapshot(db_session) -> None:
    """The constraints exist in PostgreSQL, not just in the model definition."""
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    world = await _seed_world(db_session)
    # Read the id before the first rollback: a rollback expires ORM attributes, and
    # touching one afterwards is IO that cannot happen in a sync expression.
    estate_a_id = world.estate_a.estate_id
    insert = text(
        "INSERT INTO living_score_snapshots "
        "(estate_id, engine_version, as_of, window_start, status, overall_score, "
        " measured_weight, inputs, explanation) "
        "VALUES (:estate_id, '1.0.0', now(), now(), :status, :overall, :weight, "
        " CAST(:inputs AS jsonb), CAST(:explanation AS jsonb))"
    )

    async def attempt(*, status: str, overall, weight: str = "1.00", estate_id: int | None = None) -> bool:
        try:
            await db_session.execute(
                insert,
                {
                    "estate_id": estate_a_id if estate_id is None else estate_id,
                    "status": status,
                    "overall": overall,
                    "weight": weight,
                    "inputs": "{}",
                    "explanation": "{}",
                },
            )
            await db_session.commit()
        except IntegrityError:
            await db_session.rollback()
            return True
        return False

    # A row claiming a score with nothing to show.
    assert await attempt(status="scored", overall=None) is True
    # A row admitting it cannot score while claiming a score.
    assert await attempt(status="insufficient_data", overall=50) is True
    # A score outside [0, 100].
    assert await attempt(status="scored", overall=101) is True
    assert await attempt(status="scored", overall=-1) is True
    # A status outside the engine's vocabulary.
    assert await attempt(status="finished", overall=50) is True
    # An estate that does not exist (the RESTRICT foreign key is real).
    assert await attempt(status="scored", overall=50, estate_id=999999) is True
    # The honest combination is accepted, so the checks reject only nonsense.
    assert await attempt(status="scored", overall=50) is False
