"""FACTS: everything the brief is allowed to know (BATCH AI-4).

``build_brief_facts`` is a **pure function of stored data**. It reads the latest
snapshot row (and, optionally, the two comparison snapshots the service already
loaded) and produces a small, strictly numeric object. Nothing is recalculated,
no aggregate is re-queried, and no free text is carried: the engine's prose
(``benchmark``, ``explanation``, ``recommendation``) stays on the snapshot where
it is already stored, and is read by the template layer instead.

Two properties matter and both are tested:

* **Numbers only.** Every stored value is coerced to ``Decimal``/``int``. A string
  that is not a number - a complaint description, a name, an injected instruction -
  raises ``ValueError`` rather than riding into a prompt.
* **Determinism.** The same snapshots always produce the same facts, so the same
  brief text can be reproduced and grounded against.

Deltas are computed **here**, from the stored comparison snapshots, and never by
the provider: ``previous_30d`` is the latest snapshot with
``as_of <= current.as_of - 30 days`` and ``previous_90d`` the same at 90 days.
Each delta is paired with its absolute value, because a brief may say "down 1.13"
or "1.13" and both are the same fact.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.engine import COMPONENT_KEYS, COMPONENT_WEIGHTS, WINDOW_DAYS

#: The five engine component keys, as a closed enum for the facts and the output.
ComponentKey = Literal[*COMPONENT_KEYS]

#: The two windows a brief compares against, in days.
COMPARISON_DAYS: Final[tuple[int, int]] = (30, 90)

CENT: Final[Decimal] = Decimal("0.01")
_HUNDRED: Final[Decimal] = Decimal("100")

#: The engine clamps every score to this range (the Living Score skill's bounded-
#: score requirement, and decision D3's coverage floor). Declared to the brief so
#: that "83.32 out of 100" is grounded in a supplied number rather than implied.
SCORE_MIN: Final[int] = 0
SCORE_MAX: Final[int] = 100

_FACTS_CONFIG = ConfigDict(extra="forbid", frozen=True)


class BriefOverall(BaseModel):
    """The composite score, its status, and how it moved."""

    model_config = _FACTS_CONFIG

    #: NULL means "too little of the estate was measurable" (engine decision D3).
    score: Decimal | None
    status: Literal["scored", "insufficient_data"]
    delta_30d: Decimal | None = None
    delta_30d_abs: Decimal | None = None
    delta_90d: Decimal | None = None
    delta_90d_abs: Decimal | None = None


class BriefComponent(BaseModel):
    """One component: its weight, its score and the aggregates it consumed."""

    model_config = _FACTS_CONFIG

    key: ComponentKey
    #: The component's share of the total, as a percentage (0.30 -> 30.00).
    weight_pct: Decimal
    status: Literal["measured", "insufficient_data"]
    #: NULL when the component had too little evidence - never a zero.
    score: Decimal | None
    #: The window aggregates the engine used, as numbers. Never text.
    inputs: dict[str, Decimal | int | None] = Field(default_factory=dict)
    delta_30d: Decimal | None = None
    delta_30d_abs: Decimal | None = None
    delta_90d: Decimal | None = None
    delta_90d_abs: Decimal | None = None


class BriefFacts(BaseModel):
    """The complete, closed description of one estate's latest score."""

    model_config = _FACTS_CONFIG

    engine_version: str
    as_of: datetime
    window_days: int = WINDOW_DAYS
    compared_days: tuple[int, int] = COMPARISON_DAYS
    score_min: int = SCORE_MIN
    score_max: int = SCORE_MAX
    overall: BriefOverall
    measured_weight: Decimal
    components: list[BriefComponent]


def build_brief_facts(
    snapshot: Any,
    previous_30d: Any = None,
    previous_90d: Any = None,
) -> BriefFacts:
    """Project a stored snapshot (and its two comparisons) into FACTS.

    ``snapshot`` is a ``LivingScoreSnapshot`` row; ``previous_30d`` and
    ``previous_90d`` are the comparison rows the calling service loaded, or
    ``None`` when the estate has no snapshot that old.
    """
    stored = _stored_components(snapshot)
    components = [
        _component_facts(
            key,
            stored.get(key),
            previous_30d=previous_30d,
            previous_90d=previous_90d,
        )
        for key in COMPONENT_KEYS
    ]

    overall_score = _optional_number(getattr(snapshot, "overall_score", None))
    delta_30d, delta_30d_abs = _delta(
        overall_score, _optional_number(getattr(previous_30d, "overall_score", None))
    )
    delta_90d, delta_90d_abs = _delta(
        overall_score, _optional_number(getattr(previous_90d, "overall_score", None))
    )

    return BriefFacts(
        engine_version=str(getattr(snapshot, "engine_version", "")),
        as_of=snapshot.as_of,
        overall=BriefOverall(
            score=overall_score,
            status=_status(getattr(snapshot, "status", None)),
            delta_30d=delta_30d,
            delta_30d_abs=delta_30d_abs,
            delta_90d=delta_90d,
            delta_90d_abs=delta_90d_abs,
        ),
        measured_weight=_number(getattr(snapshot, "measured_weight", 0)),
        components=components,
    )


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #
def _stored_components(snapshot: Any) -> dict[str, dict[str, Any]]:
    """The per-component breakdown stored on the snapshot, keyed by component."""
    explanation = getattr(snapshot, "explanation", None) or {}
    if not isinstance(explanation, dict):
        raise ValueError("A snapshot explanation must be a JSON object.")
    raw = explanation.get("components") or []
    if not isinstance(raw, list):
        raise ValueError("A snapshot explanation's components must be a list.")
    return {
        component["key"]: component
        for component in raw
        if isinstance(component, dict) and isinstance(component.get("key"), str)
    }


def _component_facts(
    key: str,
    stored: dict[str, Any] | None,
    *,
    previous_30d: Any,
    previous_90d: Any,
) -> BriefComponent:
    """One component's facts. A missing stored component reads as no evidence."""
    weight_pct = _round2(COMPONENT_WEIGHTS[key] * _HUNDRED)
    if stored is None:
        return BriefComponent(
            key=key, weight_pct=weight_pct, status="insufficient_data", score=None
        )

    status = _component_status(stored.get("status"))
    score = _optional_number(stored.get("score")) if status == "measured" else None

    delta_30d, delta_30d_abs = _delta(score, _previous_component_score(previous_30d, key))
    delta_90d, delta_90d_abs = _delta(score, _previous_component_score(previous_90d, key))

    return BriefComponent(
        key=key,
        weight_pct=weight_pct,
        status=status,
        score=score,
        inputs=_inputs(key, stored.get("raw_inputs")),
        delta_30d=delta_30d,
        delta_30d_abs=delta_30d_abs,
        delta_90d=delta_90d,
        delta_90d_abs=delta_90d_abs,
    )


def _inputs(key: str, raw: Any) -> dict[str, Decimal | int | None]:
    """The stored aggregates, coerced to numbers. Anything else is refused."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"Stored inputs for '{key}' must be a JSON object.")
    return {
        name: _optional_number(value, field=f"{key}.{name}")
        for name, value in raw.items()
    }


def _previous_component_score(previous: Any, key: str) -> Decimal | None:
    """A comparison snapshot's component score, read from its own column."""
    if previous is None:
        return None
    return _optional_number(getattr(previous, f"{key}_score", None))


def _delta(
    current: Decimal | None, previous: Decimal | None
) -> tuple[Decimal | None, Decimal | None]:
    """``(delta, |delta|)``, or ``(None, None)`` when either side is missing."""
    if current is None or previous is None:
        return None, None
    value = _round2(current - previous)
    return value, abs(value)


def _status(value: Any) -> str:
    if value in ("scored", "insufficient_data"):
        return str(value)
    raise ValueError(f"Unknown snapshot status: {value!r}.")


def _component_status(value: Any) -> str:
    if value in ("measured", "insufficient_data"):
        return str(value)
    raise ValueError(f"Unknown component status: {value!r}.")


def _optional_number(value: Any, *, field: str = "value") -> Decimal | int | None:
    if value is None:
        return None
    return _number(value, field=field)


def _number(value: Any, *, field: str = "value") -> Decimal | int:
    """Coerce a stored value to a number, or refuse it.

    Snapshots store ``Decimal`` as a string (7B's JSON shaping), so numeric
    strings are expected. Anything that is not a number - a name, a description,
    an injected instruction - raises rather than being carried into a prompt.
    """
    if isinstance(value, bool):
        raise ValueError(f"Stored {field} must be a number, not a boolean.")
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError):
            raise ValueError(f"Stored {field} must be a number, not free text.") from None
    raise ValueError(f"Stored {field} must be a number, not {type(value).__name__}.")


def _round2(value: Decimal) -> Decimal:
    """Two decimal places, half up - the engine's D5 rounding."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)
