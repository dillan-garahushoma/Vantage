"""Vocabulary, schema, migration and API contract tests for AI-3.

No database: the model is inspected directly, the migration is rendered to
offline SQL, and the HTTP contract is read from the application's OpenAPI
document.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.community.domain import triage_vocabulary as vocab
from app.community.models.complaint_ai_suggestion import ComplaintAISuggestion
from app.community.repositories.complaint_ai_suggestion_repository import (
    ComplaintAISuggestionRepository,
)
from app.community.schemas.complaint_ai import TriageDecisionRequest, TriageSuggestionResponse
from app.main import app

BACKEND_DIR = Path(__file__).resolve().parent.parent
REVISION = "f6c9d3a8b2e1"  # the head this batch migrates from

SUGGESTION_PATH = "/api/v1/complaints/{complaint_id}/ai-suggestion"
DECISION_PATH = "/api/v1/complaints/{complaint_id}/ai-suggestion/decision"


# ----------------------------------------------------------------- vocabulary


def test_vocabulary_matches_the_batch() -> None:
    assert vocab.CATEGORIES == (
        "water",
        "electrical",
        "security",
        "noise",
        "infrastructure",
        "gardens",
        "waste",
        "parking",
        "administrative",
        "other",
    )
    assert vocab.PRIORITIES == ("low", "normal", "high", "urgent")
    assert vocab.TRADES == (
        "plumber",
        "electrician",
        "security",
        "landscaping",
        "general_maintenance",
        "pest_control",
        "roofing",
        "other",
    )
    assert vocab.DECISIONS == ("accepted", "overridden", "dismissed")
    assert vocab.PROMPT_VERSION == "triage-v1"


def test_complaint_priority_is_built_from_the_vocabulary() -> None:
    from typing import get_args

    from app.community.schemas.complaint import ComplaintCreate

    annotation = ComplaintCreate.model_fields["priority"].annotation
    assert set(get_args(annotation)) == set(vocab.PRIORITIES)


def test_vocabulary_has_no_duplicates() -> None:
    for values in (vocab.CATEGORIES, vocab.PRIORITIES, vocab.TRADES, vocab.DECISIONS):
        assert len(values) == len(set(values)), values


def test_membership_helpers() -> None:
    assert vocab.is_valid_category("water")
    assert not vocab.is_valid_category("plumbing")
    assert not vocab.is_valid_category(None)
    assert vocab.is_valid_priority("urgent")
    assert not vocab.is_valid_priority("catastrophic")
    assert vocab.is_valid_trade("plumber")
    assert vocab.is_valid_trade(None)
    assert not vocab.is_valid_trade("welder")


def test_prompt_version_fits_the_column() -> None:
    assert len(vocab.PROMPT_VERSION) <= 32


# --------------------------------------------------------------- llm contract


def test_suggestion_schema_is_built_from_the_vocabulary() -> None:
    schema = vocab.suggestion_schema()

    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["category"]["enum"] == list(vocab.CATEGORIES)
    assert schema["properties"]["priority"]["enum"] == list(vocab.PRIORITIES)
    trade_types = schema["properties"]["trade"]
    assert set(trade_types["enum"]) - {None} == set(vocab.TRADES)
    assert None in trade_types["enum"]
    assert set(schema["required"]) == {"category", "priority", "trade"}


def test_suggestion_schema_is_a_fresh_object_every_call() -> None:
    first = vocab.suggestion_schema()
    first["properties"]["category"]["enum"].append("injected")
    first["properties"]["extra"] = {"type": "string"}

    second = vocab.suggestion_schema()
    assert second["properties"]["category"]["enum"] == list(vocab.CATEGORIES)
    assert "extra" not in second["properties"]


def test_the_ai_client_contract_offers_no_tools() -> None:
    """The LLM never has tools: the only way in is a schema plus two strings."""
    import inspect

    from app.core.ai.client import LLMClient
    from app.core.ai.guard import GuardedLLMClient

    assert set(inspect.signature(LLMClient.generate_json).parameters) == {
        "self",
        "system",
        "user",
        "schema",
        "data_class",
        "feature",
    }
    assert set(inspect.signature(GuardedLLMClient.generate_json).parameters) == {
        "self",
        "estate_id",
        "system",
        "user",
        "schema",
        "data_class",
        "feature",
    }


# ---------------------------------------------------------------------- model


def test_suggestion_table_shape() -> None:
    columns = ComplaintAISuggestion.__table__.c

    assert ComplaintAISuggestion.__tablename__ == "complaint_ai_suggestions"
    assert set(columns.keys()) == {
        "suggestion_id",
        "complaint_id",
        "estate_id",
        "suggested_category",
        "suggested_priority",
        "suggested_trade",
        "provider",
        "model",
        "prompt_version",
        "created_at",
        "decision",
        "decided_by",
        "decided_at",
        "decided_category",
        "decided_priority",
        "decided_trade",
    }
    for name in ("complaint_id", "estate_id", "suggested_category", "suggested_priority"):
        assert columns[name].nullable is False, name
    for name in (
        "suggested_trade",
        "decision",
        "decided_by",
        "decided_at",
        "decided_category",
        "decided_priority",
        "decided_trade",
    ):
        assert columns[name].nullable is True, name


def test_suggestion_table_stores_no_free_text() -> None:
    """The suggestion row keeps labels, never a prompt, response or complaint text."""
    columns = {name.lower() for name in ComplaintAISuggestion.__table__.c.keys()}

    for forbidden in ("description", "prompt", "response", "text", "body", "payload"):
        assert forbidden not in columns, forbidden


def test_complaint_id_is_unique_so_there_is_one_suggestion_per_complaint() -> None:
    uniques = [
        c
        for c in ComplaintAISuggestion.__table__.constraints
        if isinstance(c, UniqueConstraint)
    ]
    assert [c.name for c in uniques] == ["uq_complaint_ai_suggestions_complaint_id"]
    assert {col.name for col in uniques[0].columns} == {"complaint_id"}


def test_foreign_keys_use_the_right_delete_actions() -> None:
    fks = {
        c.name: c
        for c in ComplaintAISuggestion.__table__.constraints
        if isinstance(c, ForeignKeyConstraint)
    }

    assert fks["fk_complaint_ai_suggestions_complaint_id_complaints"].ondelete == "CASCADE"
    assert fks["fk_complaint_ai_suggestions_estate_id_estates"].ondelete == "RESTRICT"
    assert fks["fk_complaint_ai_suggestions_decided_by_users"].ondelete == "SET NULL"


def test_check_constraints_cover_the_vocabulary_and_the_decision() -> None:
    checks = {
        c.name: str(c.sqltext)
        for c in ComplaintAISuggestion.__table__.constraints
        if isinstance(c, CheckConstraint)
    }

    assert set(checks) == {
        "ck_complaint_ai_suggestions_suggested_category",
        "ck_complaint_ai_suggestions_suggested_priority",
        "ck_complaint_ai_suggestions_suggested_trade",
        "ck_complaint_ai_suggestions_decision",
        "ck_complaint_ai_suggestions_decided_category",
        "ck_complaint_ai_suggestions_decided_priority",
        "ck_complaint_ai_suggestions_decided_trade",
    }
    assert "administrative" in checks["ck_complaint_ai_suggestions_suggested_category"]
    assert "urgent" in checks["ck_complaint_ai_suggestions_suggested_priority"]
    assert "roofing" in checks["ck_complaint_ai_suggestions_suggested_trade"]
    assert "IS NULL OR" in checks["ck_complaint_ai_suggestions_suggested_trade"]
    assert "overridden" in checks["ck_complaint_ai_suggestions_decision"]


def test_index_supports_the_unreviewed_queue_query() -> None:
    names = {index.name for index in ComplaintAISuggestion.__table__.indexes}
    assert "ix_complaint_ai_suggestions_estate_id_decision" in names
    index = next(
        i for i in ComplaintAISuggestion.__table__.indexes
        if i.name == "ix_complaint_ai_suggestions_estate_id_decision"
    )
    assert [column.name for column in index.columns] == ["estate_id", "decision"]


# ---------------------------------------------------------------- repository


def test_decision_write_is_estate_scoped_and_write_once() -> None:
    from sqlalchemy.dialects import postgresql

    statement = ComplaintAISuggestionRepository.decision_statement(
        suggestion_id=7,
        estate_id=1,
        decision="dismissed",
        decided_by=3,
        decided_category=None,
        decided_priority=None,
        decided_trade=None,
    )
    sql = str(
        statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )

    assert "UPDATE complaint_ai_suggestions" in sql
    assert "suggestion_id = 7" in sql
    assert "estate_id = 1" in sql
    # Write-once: a second writer matches nothing and changes no row.
    assert "decision IS NULL" in sql
    assert "dismissed" in sql


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


def test_offline_upgrade_sql_creates_the_suggestion_table() -> None:
    result = _offline_sql("upgrade", "head", "--sql")

    assert result.returncode == 0, result.stderr
    sql = result.stdout
    assert "CREATE TABLE complaint_ai_suggestions" in sql
    assert "ck_complaint_ai_suggestions_suggested_category" in sql
    assert "uq_complaint_ai_suggestions_complaint_id" in sql
    assert "fk_complaint_ai_suggestions_complaint_id_complaints" in sql
    assert "fk_complaint_ai_suggestions_decided_by_users" in sql
    assert "CREATE INDEX ix_complaint_ai_suggestions_estate_id_decision" in sql


def test_offline_downgrade_sql_reverses_this_migration() -> None:
    result = _offline_sql("downgrade", f"head:{REVISION}", "--sql")

    assert result.returncode == 0, result.stderr
    assert "DROP TABLE complaint_ai_suggestions" in result.stdout


# --------------------------------------------------------------- API contract


def test_the_three_triage_routes_are_registered() -> None:
    paths = app.openapi()["paths"]

    assert set(paths[SUGGESTION_PATH]) == {"get", "post"}
    assert "post" in paths[DECISION_PATH]


def test_the_suggestion_response_contract_has_no_prompt_field() -> None:
    schema = TriageSuggestionResponse.model_json_schema()
    properties = set(schema["properties"])

    for forbidden in ("prompt", "system_prompt", "user_prompt", "raw_response", "description"):
        assert forbidden not in properties, forbidden
    assert {"suggested_category", "suggested_priority", "suggested_trade"} <= properties
    assert {"provider", "model", "prompt_version"} <= properties
    assert {"decision", "decided_by", "decided_at"} <= properties
    assert {"decided_category", "decided_priority", "decided_trade"} <= properties


def test_the_decision_request_rejects_values_outside_the_vocabulary() -> None:
    with pytest.raises(ValidationError):
        TriageDecisionRequest(decision="overridden", category="plumbing")
    with pytest.raises(ValidationError):
        TriageDecisionRequest(decision="overridden", priority="catastrophic")
    with pytest.raises(ValidationError):
        TriageDecisionRequest(decision="overridden", trade="welder")
    with pytest.raises(ValidationError):
        TriageDecisionRequest(decision="approved")


def test_the_decision_request_accepts_vocabulary_values() -> None:
    payload = TriageDecisionRequest(
        decision="overridden", category="electrical", priority="high", trade="other"
    )
    assert payload.category == "electrical"
    assert TriageDecisionRequest(decision="accepted").category is None


def test_the_decision_request_requires_the_decision() -> None:
    with pytest.raises(ValidationError):
        TriageDecisionRequest()  # type: ignore[call-arg]
