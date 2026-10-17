"""Controlled vocabulary for stored AI briefs (BATCH AI-4).

Dependency-free, like the other vocabulary modules: the ORM check constraints and
the migration are both built from these constants, so the model and the database
cannot describe different rules. The one import - ``sql_in`` - is the identical
helper used by the snapshot vocabulary, so the SQL-rendering has a single
implementation.

Nothing here computes anything, and nothing here knows about a database. The
``data_origin`` mapping exists so that "a seeded demonstration estate" is decided
in exactly one place, and the tables can never disagree about what ``demo`` means.
"""
from __future__ import annotations

from typing import Final

from app.analytics.domain.snapshot_vocabulary import sql_in

__all__ = [
    "DATA_ORIGINS",
    "DATA_ORIGIN_DEMO",
    "DATA_ORIGIN_LIVE",
    "FEEDBACK_COMMENT_MAX_LENGTH",
    "INSIGHT_KINDS",
    "KIND_HEALTH_BRIEF",
    "comment_length_check",
    "data_origin_check",
    "data_origin_for",
    "json_object_check",
    "kind_check",
    "sql_in",
]

#: The only kind of stored insight this system writes.
KIND_HEALTH_BRIEF: Final[str] = "health_brief"
INSIGHT_KINDS: Final[tuple[str, ...]] = (KIND_HEALTH_BRIEF,)

#: Where an insight's numbers came from. Copied from ``estates.is_demo`` when the
#: brief is created, so the flag is a fact about creation time, not about now.
DATA_ORIGIN_DEMO: Final[str] = "demo"
DATA_ORIGIN_LIVE: Final[str] = "live"
DATA_ORIGINS: Final[tuple[str, ...]] = (DATA_ORIGIN_DEMO, DATA_ORIGIN_LIVE)

#: A resident's feedback comment is short by design and stored locally. It is
#: never sent to a provider, so this bound is about storage hygiene, not privacy.
FEEDBACK_COMMENT_MAX_LENGTH: Final[int] = 500


def data_origin_for(*, is_demo: bool) -> str:
    """Map ``estates.is_demo`` to the stored ``data_origin``."""
    return DATA_ORIGIN_DEMO if is_demo else DATA_ORIGIN_LIVE


def kind_check() -> str:
    """A NOT NULL check body for the ``kind`` column."""
    return sql_in("kind", INSIGHT_KINDS)


def data_origin_check() -> str:
    """A NOT NULL check body for the ``data_origin`` column."""
    return sql_in("data_origin", DATA_ORIGINS)


def comment_length_check() -> str:
    """A nullable CHECK body: no comment, or a short one."""
    return (
        f"comment IS NULL OR char_length(comment) <= {FEEDBACK_COMMENT_MAX_LENGTH}"
    )


def json_object_check(column: str) -> str:
    """A JSONB column must hold an object, never an array or a scalar.

    The API contract is built around ``facts`` and ``output`` being objects; a
    scalar in either column would be unreadable, so the database refuses it.
    """
    return f"jsonb_typeof({column}) = 'object'"
