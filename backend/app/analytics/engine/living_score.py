"""The Living Score v1.0.0 calculation: pure functions, Decimal only.

Rules this module keeps, deliberately:

* **No clock.** `as_of` is a parameter, so the same inputs always produce the
  same score and a snapshot can be recalculated exactly.
* **No database.** Aggregates in, a value object out. The engine never imports
  the ORM or a repository.
* **No float.** Every intermediate is a `Decimal`; rounding happens once, at the
  boundary, with `ROUND_HALF_UP` (decision D5).
* **No invention.** Where the spec is silent the behaviour is a recorded v1.0.0
  decision in `constants.py` (see D1-D6), not a guess buried in the arithmetic.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from app.analytics.engine.constants import (
    BENCHMARKS,
    COMPONENT_KEYS,
    COMPONENT_LABELS,
    COMPONENT_WEIGHTS,
    ENGINE_VERSION,
    FREQUENCY_WORST_PER_UNIT,
    INFRASTRUCTURE_COMPLETION_WEIGHT,
    INFRASTRUCTURE_PROVIDER_WEIGHT,
    MEASURED_WEIGHT_FLOOR,
    MIN_COVERAGE_DAYS,
    MIN_RATINGS,
    MIN_RESOLVED_COMPLAINTS,
    MIN_UNITS,
    MIN_WORK_ORDERS,
    RECOMMENDATIONS,
    RECOMMENDATION_BELOW,
    RESOLUTION_BEST_DAYS,
    RESOLUTION_WORST_DAYS,
    ROUNDING,
    SATISFACTION_MAX_RATING,
    SATISFACTION_MIN_RATING,
    SECURITY_WORST_INCIDENTS,
    WINDOW_DAYS,
)
from app.analytics.engine.models import (
    ComponentResult,
    ComponentStatus,
    EstateScoreInputs,
    ScoreResult,
)

_ZERO = Decimal("0")
_HUNDRED = Decimal("100")


def _aware(moment: datetime) -> datetime:
    """Treat a naive timestamp as UTC; normalise an aware one to UTC."""
    if moment.tzinfo is None or moment.utcoffset() is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def window_bounds(as_of: datetime) -> tuple[datetime, datetime]:
    """The rolling 90-day window `[start, end]`, both ends inclusive (D1)."""
    end = _aware(as_of)
    return end - timedelta(days=WINDOW_DAYS), end


def in_window(moment: datetime, as_of: datetime) -> bool:
    """Is ``moment`` inside the window? Boundary values count (D1).

    Provided so the database layer filters with exactly the definition the engine
    scores with, instead of re-deriving the window and drifting.
    """
    start, end = window_bounds(as_of)
    return start <= _aware(moment) <= end


def _clamp(value: Decimal) -> Decimal:
    """Every sub-score and the composite are bounded to [0, 100]."""
    return max(_ZERO, min(_HUNDRED, value))


def _round2(value: Decimal) -> Decimal:
    return value.quantize(ROUNDING, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class _Outcome:
    """One component's unrounded result; the aggregator rounds and weights it."""

    status: ComponentStatus
    unrounded: Decimal | None
    raw_inputs: dict
    explanation: str


def _insufficient(explanation: str, raw_inputs: dict) -> _Outcome:
    return _Outcome("insufficient_data", None, raw_inputs, explanation)


def _measured(unrounded: Decimal, raw_inputs: dict, explanation: str) -> _Outcome:
    return _Outcome("measured", unrounded, raw_inputs, explanation)


# --------------------------------------------------------------------------- #
# The five components
# --------------------------------------------------------------------------- #
def _resolution(inputs: EstateScoreInputs) -> _Outcome:
    """Average complaint resolution days: 1 day = 100, 30 days or more = 0."""
    raw = {
        "avg_resolution_days": inputs.avg_resolution_days,
        "resolved_complaints": inputs.resolved_complaints,
    }
    if inputs.resolved_complaints < MIN_RESOLVED_COMPLAINTS or inputs.avg_resolution_days is None:
        return _insufficient(
            "Only "
            f"{inputs.resolved_complaints} complaint(s) were resolved in the window; "
            f"at least {MIN_RESOLVED_COMPLAINTS} are needed before an average "
            "resolution time is meaningful.",
            raw,
        )

    days = inputs.avg_resolution_days
    unrounded = _HUNDRED * (RESOLUTION_WORST_DAYS - days) / (
        RESOLUTION_WORST_DAYS - RESOLUTION_BEST_DAYS
    )
    score = _clamp(unrounded)
    return _measured(
        score,
        raw,
        f"{inputs.resolved_complaints} complaints resolved, averaging {_round2(days)} days; "
        f"scores {_round2(score)} out of 100 ({BENCHMARKS['resolution']})",
    )


def _frequency(inputs: EstateScoreInputs) -> _Outcome:
    """Complaints per unit: 0 per unit = 100, 5 or more per unit = 0."""
    per_unit = (
        Decimal(inputs.complaints_created) / Decimal(inputs.unit_count)
        if inputs.unit_count
        else None
    )
    raw = {
        "complaints_created": inputs.complaints_created,
        "unit_count": inputs.unit_count,
        "coverage_days": inputs.coverage_days,
        "complaints_per_unit": _round2(per_unit) if per_unit is not None else None,
    }
    if inputs.coverage_days < MIN_COVERAGE_DAYS or inputs.unit_count < MIN_UNITS:
        return _insufficient(
            f"{inputs.coverage_days} day(s) of history over {inputs.unit_count} unit(s); "
            f"at least {MIN_COVERAGE_DAYS} days and {MIN_UNITS} unit are needed before "
            "complaint frequency says anything about the estate.",
            raw,
        )

    assert per_unit is not None
    unrounded = _HUNDRED * (Decimal("1") - per_unit / FREQUENCY_WORST_PER_UNIT)
    score = _clamp(unrounded)
    return _measured(
        score,
        raw,
        f"{inputs.complaints_created} complaints over {inputs.unit_count} units in "
        f"{inputs.coverage_days} days is {_round2(per_unit)} per unit; scores "
        f"{_round2(score)} out of 100 ({BENCHMARKS['frequency']})",
    )


def _security(inputs: EstateScoreInputs) -> _Outcome:
    """Incidents in the window: 0 = 100, 15 or more = 0 (D6: raw count, no scaling)."""
    raw = {
        "incidents": inputs.incidents,
        "coverage_days": inputs.coverage_days,
        "unit_count": inputs.unit_count,
    }
    if inputs.coverage_days < MIN_COVERAGE_DAYS or inputs.unit_count < MIN_UNITS:
        return _insufficient(
            f"{inputs.coverage_days} day(s) of history over {inputs.unit_count} unit(s); "
            f"at least {MIN_COVERAGE_DAYS} days and {MIN_UNITS} unit are needed before "
            "a security record means anything.",
            raw,
        )

    unrounded = _HUNDRED * (
        Decimal("1") - Decimal(inputs.incidents) / SECURITY_WORST_INCIDENTS
    )
    score = _clamp(unrounded)
    return _measured(
        score,
        raw,
        f"{inputs.incidents} incident(s) recorded in the window; scores "
        f"{_round2(score)} out of 100 ({BENCHMARKS['security']})",
    )


def _satisfaction(inputs: EstateScoreInputs) -> _Outcome:
    """Average resident rating on completed work orders: 1 star = 0, 5 stars = 100."""
    raw = {"avg_rating": inputs.avg_rating, "rated_count": inputs.rated_count}
    if inputs.rated_count < MIN_RATINGS or inputs.avg_rating is None:
        return _insufficient(
            f"Only {inputs.rated_count} rated work order(s) in the window; at least "
            f"{MIN_RATINGS} are needed before resident satisfaction is meaningful.",
            raw,
        )

    rating = inputs.avg_rating
    unrounded = _HUNDRED * (rating - SATISFACTION_MIN_RATING) / (
        SATISFACTION_MAX_RATING - SATISFACTION_MIN_RATING
    )
    score = _clamp(unrounded)
    return _measured(
        score,
        raw,
        f"{inputs.rated_count} rated work orders averaging {_round2(rating)} stars; "
        f"scores {_round2(score)} out of 100 ({BENCHMARKS['satisfaction']})",
    )


def _infrastructure(inputs: EstateScoreInputs) -> _Outcome:
    """Completed work orders (70%) blended with the provider rating (30%) (D4)."""
    raw = {
        "work_orders_in_window": inputs.work_orders_in_window,
        "work_orders_completed": inputs.work_orders_completed,
        "avg_provider_rating": inputs.avg_provider_rating,
        "provider_rating_count": inputs.provider_rating_count,
    }
    if inputs.work_orders_in_window < MIN_WORK_ORDERS:
        return _insufficient(
            "No work orders were raised in the window, so there is nothing to say "
            "about maintenance throughput.",
            raw,
        )

    completed_pct = (
        Decimal(inputs.work_orders_completed) / Decimal(inputs.work_orders_in_window) * _HUNDRED
    )
    has_provider_data = (
        inputs.provider_rating_count > 0 and inputs.avg_provider_rating is not None
    )
    if has_provider_data:
        assert inputs.avg_provider_rating is not None
        provider_score = _HUNDRED * (inputs.avg_provider_rating - SATISFACTION_MIN_RATING) / (
            SATISFACTION_MAX_RATING - SATISFACTION_MIN_RATING
        )
        unrounded = (
            INFRASTRUCTURE_COMPLETION_WEIGHT * completed_pct
            + INFRASTRUCTURE_PROVIDER_WEIGHT * provider_score
        )
        note = (
            f"blended {int(INFRASTRUCTURE_COMPLETION_WEIGHT * 100)}% completion / "
            f"{int(INFRASTRUCTURE_PROVIDER_WEIGHT * 100)}% provider rating "
            f"({_round2(inputs.avg_provider_rating)} stars from "
            f"{inputs.provider_rating_count} rating(s))"
        )
    else:
        unrounded = completed_pct
        note = (
            "the provider-rating half of the blend was omitted because no provider "
            "rating data is available for this window, so completion alone was used"
        )

    score = _clamp(unrounded)
    return _measured(
        score,
        raw,
        f"{inputs.work_orders_completed} of {inputs.work_orders_in_window} work orders "
        f"completed ({_round2(completed_pct)}%); {note}; scores {_round2(score)} out of 100",
    )


_CALCULATORS = {
    "resolution": _resolution,
    "frequency": _frequency,
    "security": _security,
    "satisfaction": _satisfaction,
    "infrastructure": _infrastructure,
}


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #
def calculate_living_score(inputs: EstateScoreInputs) -> ScoreResult:
    """Score one estate over the 90 days ending at ``inputs.as_of``.

    Pure and total: the same inputs always give the same result, and nothing
    raises for missing data - a component with too little evidence is marked
    `insufficient_data`, and if too little of the estate was measurable the
    overall score is `None` rather than a misleading number (D2/D3).
    """
    window_start, window_end = window_bounds(inputs.as_of)
    outcomes = {key: _CALCULATORS[key](inputs) for key in COMPONENT_KEYS}

    measured = [key for key in COMPONENT_KEYS if outcomes[key].status == "measured"]
    measured_weight = sum((COMPONENT_WEIGHTS[key] for key in measured), start=_ZERO)
    has_overall = measured_weight >= MEASURED_WEIGHT_FLOOR

    components: list[ComponentResult] = []
    for key in COMPONENT_KEYS:
        outcome = outcomes[key]
        weight = COMPONENT_WEIGHTS[key]
        if outcome.status != "measured" or outcome.unrounded is None:
            components.append(
                ComponentResult(
                    key=key,
                    weight=weight,
                    status="insufficient_data",
                    score=None,
                    raw_inputs=outcome.raw_inputs,
                    benchmark=BENCHMARKS[key],
                    contribution=None,
                    lost_points=None,
                    explanation=outcome.explanation,
                    recommendation=None,
                )
            )
            continue

        score = _round2(_clamp(outcome.unrounded))
        # Contribution and lost points are computed from the unrounded score and
        # the measured weight (D5), so they reconcile with the overall score.
        contribution = _round2(weight * outcome.unrounded / measured_weight)
        lost_points = _round2(
            weight * (_HUNDRED - outcome.unrounded) / measured_weight
        )
        components.append(
            ComponentResult(
                key=key,
                weight=weight,
                status="measured",
                score=score,
                raw_inputs=outcome.raw_inputs,
                benchmark=BENCHMARKS[key],
                contribution=contribution,
                lost_points=lost_points,
                explanation=outcome.explanation,
                recommendation=RECOMMENDATIONS[key] if score < RECOMMENDATION_BELOW else None,
            )
        )

    overall_score: Decimal | None = None
    if has_overall:
        weighted = sum(
            (COMPONENT_WEIGHTS[key] * outcomes[key].unrounded for key in measured),
            start=_ZERO,
        )
        overall_score = _round2(_clamp(weighted / measured_weight))

    drivers = tuple(
        sorted(
            (c for c in components if c.status == "measured"),
            key=lambda c: (-(c.lost_points or _ZERO), COMPONENT_KEYS.index(c.key)),
        )
    )

    return ScoreResult(
        engine_version=ENGINE_VERSION,
        window_start=window_start,
        window_end=window_end,
        overall_score=overall_score,
        status="scored" if has_overall else "insufficient_data",
        measured_weight=measured_weight,
        components=tuple(components),
        drivers=drivers,
    )


def describe_component(result: ScoreResult, key: str) -> str:
    """One-line human label for a component, for logs and operator views."""
    component = next(c for c in result.components if c.key == key)
    label = COMPONENT_LABELS[key]
    if component.score is None:
        return f"{label}: insufficient data"
    return f"{label}: {component.score} out of 100"
