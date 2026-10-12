"""Controlled vocabulary for security incidents (BATCH 6B).

This module is the single source of truth for what a security incident may say.
It is deliberately dependency-free: the ORM check constraints, the API request
DTOs and the query filters are all built from these tuples, so adding a value in
one place cannot drift out of sync with the others.

An incident exists for exactly one reason: to be the Living Score security
input. It is not a security-management platform - there are no assignments,
comments, attachments, notifications or workflows - and nothing here computes
anything.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Final

CATEGORIES: Final[tuple[str, ...]] = (
    "perimeter_breach",
    "access_control_failure",
    "theft",
    "vandalism",
    "trespass",
    "suspicious_activity",
    "other",
)

SEVERITIES: Final[tuple[str, ...]] = ("low", "medium", "high", "critical")

# `open` -> `investigating` -> `resolved`, and `open` -> `resolved`. `resolved`
# is terminal; the service enforces the transitions, the database enforces the
# vocabulary.
STATUSES: Final[tuple[str, ...]] = ("open", "investigating", "resolved")

DEFAULT_STATUS: Final[str] = "open"
RESOLVED_STATUS: Final[str] = "resolved"
INVESTIGATING_STATUS: Final[str] = "investigating"


def is_valid_category(value: object) -> bool:
    return isinstance(value, str) and value in CATEGORIES


def is_valid_severity(value: object) -> bool:
    return isinstance(value, str) and value in SEVERITIES


def is_valid_status(value: object) -> bool:
    return isinstance(value, str) and value in STATUSES


def sql_in(column: str, values: Sequence[str]) -> str:
    """Render a NOT NULL check constraint body for a vocabulary column."""
    rendered = ", ".join(repr(value) for value in values)
    return f"{column} IN ({rendered})"


def nullable_sql_in(column: str, values: Sequence[str]) -> str:
    """Render a nullable check constraint body: NULL passes, anything else is checked."""
    rendered = ", ".join(repr(value) for value in values)
    return f"{column} IS NULL OR {column} IN ({rendered})"


def resolution_timestamps_check() -> str:
    """A resolved incident has a resolution time, and only a resolved one does.

    Kept here (rather than inline in the model and the migration) so the two
    cannot describe different rules.
    """
    return f"(status = '{RESOLVED_STATUS}') = (resolved_at IS NOT NULL)"
