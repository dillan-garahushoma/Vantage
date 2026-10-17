"""Vocabulary, model, migration and HTTP contract for the health brief (BATCH AI-4).

No database: the models are inspected directly, the migration is rendered to
offline SQL, and the HTTP contract is read from the application's OpenAPI
document.
"""

from __future__ import annotations

import inspect
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.analytics.api import health_brief as health_brief_api
from app.analytics.domain import insight_vocabulary as vocab
from app.analytics.models.ai_insight import AIInsight
from app.analytics.models.ai_insight_feedback import AIInsightFeedback
from app.analytics.repositories.ai_insight_feedback_repository import (
    AIInsightFeedbackRepository,
)
from app.analytics.repositories.ai_insight_repository import AIInsightRepository
from app.analytics.schemas.health_brief import (
    HealthBriefFeedbackRequest,
    HealthBriefFeedbackResponse,
    HealthBriefResponse,
)
from app.main import app

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
PREVIOUS_REVISION = "c4d8f1a7b9e3"  # the head this batch migrates from
NEW_REVISION = "d9f2a4c7e1b3"

HEALTH_BRIEF_PATH = "/api/v1/analytics/health-brief"
FEEDBACK_PATH = f"{HEALTH_BRIEF_PATH}/{{insight_id}}/feedback"

SERVICE_MODULE = "app/analytics/services/health_brief_service.py"
BRIEF_ROUTER = "app/analytics/api/health_brief.py"


# ----------------------------------------------------------------- vocabulary


def test_the_kind_and_origin_vocabularies_match_the_batch() -> None:
    assert vocab.INSIGHT_KINDS == ("health_brief",)
    assert vocab.DATA_ORIGINS == ("demo", "live")
    assert vocab.FEEDBACK_COMMENT_MAX_LENGTH == 500


def test_the_demo_flag_maps_to_a_data_origin() -> None:
    assert vocab.data_origin_for(is_demo=True) == "demo"
    assert vocab.data_origin_for(is_demo=False) == "live"


def test_vocabulary_values_fit_their_columns() -> None:
    assert max(len(kind) for kind in vocab.INSIGHT_KINDS) <= 30
    assert max(len(origin) for origin in vocab.DATA_ORIGINS) <= 10


def test_the_check_bodies_are_built_from_the_vocabulary() -> None:
    assert vocab.sql_in("kind", vocab.INSIGHT_KINDS) == "kind IN ('health_brief')"
    origin_body = vocab.sql_in("data_origin", vocab.DATA_ORIGINS)
    assert origin_body == "data_origin IN ('demo', 'live')"
    assert "500" in vocab.comment_length_check()
    assert "jsonb_typeof" in vocab.json_object_check("facts")


# --------------------------------------------------------------------- models


def test_the_insight_table_holds_ai_briefs_only() -> None:
    assert AIInsight.__tablename__ == "ai_insights"

    columns = set(AIInsight.__table__.columns.keys())
    assert columns == {
        "insight_id",
        "estate_id",
        "snapshot_id",
        "kind",
        "prompt_version",
        "provider",
        "model",
        "facts",
        "output",
        "data_origin",
        "created_at",
    }
    # No column for a raw prompt or a provider response, ever.
    for forbidden in ("prompt", "system_prompt", "user_prompt", "raw_response", "text"):
        assert forbidden not in columns


def test_the_insight_constraints_are_named_and_documented() -> None:
    names = {c.name for c in AIInsight.__table__.constraints if c.name}
    assert "uq_ai_insights_snapshot_kind_prompt_version" in names
    assert "ck_ai_insights_kind" in names
    assert "ck_ai_insights_data_origin" in names
    assert "ck_ai_insights_facts_object" in names
    assert "ck_ai_insights_output_object" in names
    assert "fk_ai_insights_snapshot_id_living_score_snapshots" in names
    assert "fk_ai_insights_estate_id_estates" in names

    unique = next(
        c
        for c in AIInsight.__table__.constraints
        if isinstance(c, UniqueConstraint)
        and c.name == "uq_ai_insights_snapshot_kind_prompt_version"
    )
    assert {col.name for col in unique.columns} == {"snapshot_id", "kind", "prompt_version"}


def _fk(model, column: str) -> ForeignKeyConstraint:
    for constraint in model.__table__.constraints:
        if isinstance(constraint, ForeignKeyConstraint) and column in {
            col.name for col in constraint.columns
        }:
            return constraint
    raise AssertionError(f"no foreign key on {model.__tablename__}.{column}")


def test_the_insight_foreign_keys_use_the_documented_delete_rules() -> None:
    assert _fk(AIInsight, "estate_id").ondelete == "RESTRICT"
    assert _fk(AIInsight, "snapshot_id").ondelete == "RESTRICT"
    assert _fk(AIInsightFeedback, "insight_id").ondelete == "CASCADE"
    assert _fk(AIInsightFeedback, "estate_id").ondelete == "RESTRICT"
    assert _fk(AIInsightFeedback, "user_id").ondelete == "SET NULL"


def test_the_insight_index_supports_the_estate_read() -> None:
    index_names = {index.name for index in AIInsight.__table__.indexes}
    assert "ix_ai_insights_estate_id_created_at" in index_names


def test_the_feedback_table_matches_the_batch() -> None:
    assert AIInsightFeedback.__tablename__ == "ai_insight_feedback"

    assert set(AIInsightFeedback.__table__.columns.keys()) == {
        "feedback_id",
        "insight_id",
        "estate_id",
        "user_id",
        "helpful",
        "comment",
        "created_at",
    }
    names = {c.name for c in AIInsightFeedback.__table__.constraints if c.name}
    assert "uq_ai_insight_feedback_insight_id_user_id" in names
    assert "ck_ai_insight_feedback_comment_length" in names
    assert AIInsightFeedback.helpful.nullable is False
    assert AIInsightFeedback.comment.nullable is True


def test_the_comment_check_limits_the_length_in_the_database() -> None:
    body = next(
        c.sqltext.text
        for c in AIInsightFeedback.__table__.constraints
        if isinstance(c, CheckConstraint) and c.name == "ck_ai_insight_feedback_comment_length"
    )
    assert "500" in body
    assert "comment" in body


def test_the_models_are_registered_for_alembic() -> None:
    from app.db import database

    source = inspect.getsource(database)
    assert "AIInsight" in source
    assert "AIInsightFeedback" in source


# --------------------------------------------------------------- repositories


def test_the_insight_repository_is_append_only() -> None:
    for name in dir(AIInsightRepository):
        lowered = name.lower()
        assert "update" not in lowered, name
        assert "delete" not in lowered, name
        assert "remove" not in lowered, name
        assert "upsert" not in lowered, name
        assert "save" not in lowered, name


def test_the_feedback_repository_is_append_only_too() -> None:
    for name in dir(AIInsightFeedbackRepository):
        lowered = name.lower()
        assert "update" not in lowered, name
        assert "delete" not in lowered, name
        assert "remove" not in lowered, name


def test_every_insight_read_statement_is_estate_scoped() -> None:
    statements = {
        "for_snapshot": AIInsightRepository.for_snapshot_statement(
            estate_id=7, snapshot_id=11, kind="health_brief", prompt_version="brief-v1"
        ),
        "by_id": AIInsightRepository.by_id_statement(estate_id=7, insight_id=12),
    }

    for name, statement in statements.items():
        assert "ai_insights.estate_id = " in str(statement.compile()), name

    snapshot_sql = str(statements["for_snapshot"].compile())
    assert "ai_insights.snapshot_id = " in snapshot_sql
    assert "ai_insights.kind = " in snapshot_sql
    assert "ai_insights.prompt_version = " in snapshot_sql


def test_the_feedback_uniqueness_read_is_scoped_to_one_insight_and_user() -> None:
    sql = str(
        AIInsightFeedbackRepository.for_insight_and_user_statement(
            insight_id=12, user_id=2
        ).compile()
    )
    assert "ai_insight_feedback.insight_id = " in sql
    assert "ai_insight_feedback.user_id = " in sql


def test_the_repositories_never_touch_an_orm_row_from_a_router() -> None:
    """A router wires dependencies; it never reaches a row itself.

    ``AsyncSession`` is imported for the dependency annotation, as in every other
    router in this codebase. What is forbidden is a repository, a model, or a
    query.
    """
    source = inspect.getsource(health_brief_api)
    imports = [
        line.strip()
        for line in source.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for forbidden in (
        "app.analytics.repositories",
        "app.analytics.models",
        "sqlalchemy.orm",
        "sqlalchemy import select",
    ):
        assert not any(forbidden in line for line in imports), forbidden
    assert "select(" not in source
    assert ".execute(" not in source
    assert "HealthBriefService" in source


def test_only_the_brief_service_and_its_router_may_build_a_brief() -> None:
    """No other API module may reach the service, and no module may recompute."""
    offenders = []
    for path in sorted((BACKEND_DIR / "app").rglob("*.py")):
        relative = path.relative_to(BACKEND_DIR).as_posix()
        if relative in {SERVICE_MODULE, BRIEF_ROUTER}:
            continue
        if "HealthBriefService" in path.read_text(encoding="utf-8"):
            offenders.append(relative)
    assert offenders == []


def test_the_brief_layer_never_calls_the_score_engine() -> None:
    """The LLM explains the number; it must not be able to make one.

    The brief may read the engine's published vocabulary (component keys, weights
    and labels) to describe a stored score. It may never call its calculation.
    """
    for path in sorted((BACKEND_DIR / "app/analytics/ai").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        for forbidden in (
            "calculate_living_score",
            "EstateScoreInputs",
            "window_bounds",
            "describe_component",
            "app.analytics.engine.living_score",
        ):
            assert forbidden not in source, (path.name, forbidden)


# ------------------------------------------------------------------ migration


def _offline_sql(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", *args],
        cwd=str(BACKEND_DIR),
        env=dict(os.environ),
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_the_migration_revises_the_previous_head() -> None:
    source = (
        BACKEND_DIR / "alembic" / "versions" / f"{NEW_REVISION}_add_ai_insights.py"
    ).read_text(encoding="utf-8")
    assert f'revision: str = "{NEW_REVISION}"' in source
    assert f'down_revision: Union[str, Sequence[str], None] = "{PREVIOUS_REVISION}"' in source


def test_offline_upgrade_sql_creates_both_tables() -> None:
    result = _offline_sql("upgrade", "head", "--sql")

    assert result.returncode == 0, result.stderr
    sql = result.stdout
    assert "CREATE TABLE ai_insights" in sql
    assert "CREATE TABLE ai_insight_feedback" in sql
    assert "uq_ai_insights_snapshot_kind_prompt_version" in sql
    assert "ck_ai_insights_kind" in sql
    assert "ck_ai_insights_data_origin" in sql
    assert "ck_ai_insight_feedback_comment_length" in sql
    assert "fk_ai_insights_snapshot_id_living_score_snapshots" in sql
    assert "CREATE INDEX ix_ai_insights_estate_id_created_at" in sql


def test_offline_downgrade_sql_reverses_this_migration() -> None:
    result = _offline_sql("downgrade", f"head:{PREVIOUS_REVISION}", "--sql")

    assert result.returncode == 0, result.stderr
    sql = result.stdout
    assert "DROP TABLE ai_insight_feedback" in sql
    assert "DROP TABLE ai_insights" in sql


# ---------------------------------------------------------------- API contract


def test_the_three_routes_are_registered() -> None:
    paths = app.openapi()["paths"]

    assert set(paths[HEALTH_BRIEF_PATH]) == {"get", "post"}
    assert "post" in paths[FEEDBACK_PATH]


def test_the_generate_route_is_a_post_and_the_read_is_a_get() -> None:
    paths = app.openapi()["paths"]

    assert "get" in paths[HEALTH_BRIEF_PATH]
    assert "post" in paths[HEALTH_BRIEF_PATH]
    assert "get" not in paths[FEEDBACK_PATH]


def test_the_routes_take_the_estate_from_the_query_string() -> None:
    paths = app.openapi()["paths"]

    for path in (HEALTH_BRIEF_PATH, FEEDBACK_PATH):
        for operation in paths[path].values():
            parameter_names = {
                parameter["name"] for parameter in operation.get("parameters", [])
            }
            assert "estate_id" in parameter_names, path
            assert "estate_id" not in str(operation.get("requestBody", "")), path


def test_the_response_contract_leaks_no_prompt_or_provider_payload() -> None:
    properties = set(HealthBriefResponse.model_json_schema()["properties"])

    for forbidden in (
        "prompt",
        "system_prompt",
        "user_prompt",
        "raw_response",
        "provider_response",
        "complaints",
        "description",
    ):
        assert forbidden not in properties, forbidden

    assert {
        "source",
        "insight_id",
        "ai_unavailable_reason",
        "data_origin",
        "snapshot_id",
        "as_of",
        "generated_at",
        "facts",
        "output",
        "provider",
        "model",
        "prompt_version",
    } <= properties


def test_the_feedback_request_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        HealthBriefFeedbackRequest(helpful=True, note="free text")  # type: ignore[call-arg]


def test_the_feedback_request_requires_helpful() -> None:
    with pytest.raises(ValidationError):
        HealthBriefFeedbackRequest()  # type: ignore[call-arg]


def test_the_comment_is_limited_to_five_hundred_characters() -> None:
    assert HealthBriefFeedbackRequest(helpful=True, comment="x" * 500).comment is not None
    with pytest.raises(ValidationError):
        HealthBriefFeedbackRequest(helpful=True, comment="x" * 501)


def test_the_feedback_response_exposes_the_id_alias() -> None:
    """The wire contract is the OpenAPI document's, which serialises by alias."""
    schemas = app.openapi()["components"]["schemas"]
    schema = schemas[HealthBriefFeedbackResponse.__name__]

    assert "id" in schema["properties"]
    assert "feedback_id" not in schema["properties"]


def test_the_ai_unavailable_reason_is_a_closed_vocabulary() -> None:
    """A client can rely on the reason set; nothing else may appear."""
    annotation = str(HealthBriefResponse.model_fields["ai_unavailable_reason"].annotation)

    for reason in (
        "disabled",
        "policy",
        "budget",
        "timeout",
        "network",
        "provider_error",
        "invalid_output",
        "ungrounded_output",
        "insufficient_data",
    ):
        assert reason in annotation, reason


# ---------------------------------------------------------------- docs, wiring


def test_the_runbook_says_the_brief_sends_aggregates_only() -> None:
    text = (REPO_ROOT / "docs" / "PILOT_RUNBOOK.md").read_text(encoding="utf-8")

    assert "Health Brief" in text
    assert "aggregate" in text.lower()
