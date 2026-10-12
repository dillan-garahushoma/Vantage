"""Controlled vocabulary for advisory AI triage suggestions (BATCH AI-3).

This module is the single source of truth for what a triage suggestion may say.
It is deliberately dependency-free: the ORM check constraints, the provider JSON
schema and the API validators are all built from these tuples, so adding a value
in one place cannot drift out of sync with the others, and a provider can never
return a value the database or the API would refuse.

Nothing here computes anything. A suggestion is a label a human may accept,
override or dismiss; it never changes a complaint row.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Final, Literal

CATEGORIES: Final[tuple[str, ...]] = (
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

# Must match the existing complaints.priority check constraint.
PRIORITIES: Final[tuple[str, ...]] = ("low", "normal", "high", "urgent")

TRADES: Final[tuple[str, ...]] = (
    "plumber",
    "electrician",
    "security",
    "landscaping",
    "general_maintenance",
    "pest_control",
    "roofing",
    "other",
)

DECISIONS: Final[tuple[str, ...]] = ("accepted", "overridden", "dismissed")

PROMPT_VERSION: Final[str] = "triage-v1"

# The API-facing aliases, built from the tuples above rather than typed out again.
# FastAPI publishes a ``Literal`` of several strings as an ``enum`` array in the
# OpenAPI contract, so the client reads the allowed values instead of guessing
# them. They live here because more than one schema needs them: the triage
# decision and suggestion contracts, and complaint creation.
Category = Literal[*CATEGORIES]
Priority = Literal[*PRIORITIES]
Trade = Literal[*TRADES]
Decision = Literal[*DECISIONS]


def is_valid_category(value: object) -> bool:
    return isinstance(value, str) and value in CATEGORIES


def is_valid_priority(value: object) -> bool:
    return isinstance(value, str) and value in PRIORITIES


def is_valid_trade(value: object) -> bool:
    """``None`` is valid: a complaint may have no obvious trade."""
    return value is None or (isinstance(value, str) and value in TRADES)


def is_valid_decision(value: object) -> bool:
    return isinstance(value, str) and value in DECISIONS


def suggestion_schema() -> dict[str, Any]:
    """The JSON schema asked of the provider, built from the vocabulary.

    Returns a fresh object every call so a caller cannot mutate shared state.
    ``additionalProperties`` is false and every field is required, so provider
    output is either exactly this shape or rejected.
    """
    return {
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": list(CATEGORIES)},
            "priority": {"type": "string", "enum": list(PRIORITIES)},
            "trade": {"type": ["string", "null"], "enum": [*TRADES, None]},
        },
        "required": ["category", "priority", "trade"],
        "additionalProperties": False,
    }


def sql_in(column: str, values: Sequence[str]) -> str:
    """Render a NOT NULL check constraint body for a vocabulary column."""
    rendered = ", ".join(repr(value) for value in values)
    return f"{column} IN ({rendered})"


def nullable_sql_in(column: str, values: Sequence[str]) -> str:
    """Render a nullable check constraint body: NULL passes, anything else is checked."""
    rendered = ", ".join(repr(value) for value in values)
    return f"{column} IS NULL OR {column} IN ({rendered})"
