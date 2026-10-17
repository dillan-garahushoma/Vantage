"""Controlled vocabulary for Living Score snapshots (BATCH 7B).

Dependency-free, exactly like ``app/community/domain/incident_vocabulary.py``: the
ORM check constraints and the migration are both built from these constants, so
the model and the database cannot describe different rules.

The value vocabulary itself is owned by the engine (``scored`` /
``insufficient_data`` are its ``ScoreStatus`` values); this module only gives the
persistence layer the same words in SQL-checkable form. Nothing here computes
anything, and nothing here knows about a database.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Final

#: The two values ``status`` may take. Mirrors the engine's ``ScoreStatus``.
SNAPSHOT_STATUSES: Final[tuple[str, ...]] = ("scored", "insufficient_data")

SCORED_STATUS: Final[str] = "scored"
INSUFFICIENT_DATA_STATUS: Final[str] = "insufficient_data"

#: The five component score columns, in the engine's fixed component order.
COMPONENT_SCORE_COLUMNS: Final[tuple[str, ...]] = (
    "resolution_score",
    "frequency_score",
    "security_score",
    "satisfaction_score",
    "infrastructure_score",
)

#: Every bounded score column: the composite plus the five components.
SCORE_COLUMNS: Final[tuple[str, ...]] = ("overall_score",) + COMPONENT_SCORE_COLUMNS

SCORE_MIN: Final[int] = 0
SCORE_MAX: Final[int] = 100


def sql_in(column: str, values: Sequence[str]) -> str:
    """Render a NOT NULL check constraint body for a vocabulary column."""
    rendered = ", ".join(repr(value) for value in values)
    return f"{column} IN ({rendered})"


def scores_bounded_check() -> str:
    """Every score column sits inside [0, 100], and NULL still means "no evidence".

    NULL is allowed on a component score (it is how "insufficient data" is stored,
    never a zero) and on the overall score (which the status check below ties to
    the status column). A component that IS NULL must not be read as zero, so the
    bound only applies when a value is present.
    """
    parts = [
        f"({column} IS NULL OR ({column} >= {SCORE_MIN} AND {column} <= {SCORE_MAX}))"
        for column in SCORE_COLUMNS
    ]
    return " AND ".join(parts)


def status_matches_overall_check() -> str:
    """A scored snapshot has an overall score; an insufficient one does not.

    This is the invariant that keeps the two nullable-looking columns honest, so a
    reader can never see ``status = 'scored'`` with nothing to show.
    """
    return f"(status = '{SCORED_STATUS}') = (overall_score IS NOT NULL)"
