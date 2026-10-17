"""The deterministic template brief (BATCH AI-4).

This is the brief with the AI switched off, or with any AI failure: same shape as
a generated one, built entirely from what is already stored on the snapshot - the
engine's per-component explanations, its lost-point arithmetic and its static
recommendations, plus the deltas already computed in FACTS.

It is **never stored**. A template is rebuilt on demand from the snapshot it
describes, so it can never drift from the score, and there is no second copy of
the estate's numbers to keep honest. That also means a later AI attempt has
nothing to overwrite.

Every word here is either a number from the snapshot or a sentence the engine
itself wrote; the function invents no analysis and no advice.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Final

from app.analytics.ai.brief_facts import COMPONENT_KEYS, BriefFacts, BriefComponent
from app.analytics.ai.brief_output import (
    ACTION_MAX,
    HEADLINE_MAX,
    MAX_ACTIONS,
    MAX_DRIVERS,
    STATEMENT_MAX,
    SUMMARY_MAX,
    BriefAction,
    BriefDriver,
    BriefOutput,
)
from app.analytics.engine import COMPONENT_LABELS

#: Shown when the snapshot has no overall score (engine decision D3).
NO_SCORE_HEADLINE: Final[str] = "Living Score unavailable: too little measurable data"

_DIRECTION_PHRASE: Final[dict[str, str]] = {
    "improving": "improving over the comparison window",
    "declining": "declining over the comparison window",
    "stable": "holding steady",
}


def build_template_brief(snapshot: Any, facts: BriefFacts) -> BriefOutput:
    """Build the template brief for one snapshot from its stored explanation."""
    stored = _stored_components(snapshot)
    measured = sorted(
        (c for c in facts.components if c.status == "measured"),
        key=lambda c: (-_lost_points(stored.get(c.key)), COMPONENT_KEYS.index(c.key)),
    )

    return BriefOutput(
        headline=_headline(facts),
        summary=_summary(facts, stored, measured),
        drivers=[
            _driver(component, stored.get(component.key), facts)
            for component in measured[:MAX_DRIVERS]
        ],
        actions=_actions(stored, measured),
    )


def _headline(facts: BriefFacts) -> str:
    if facts.overall.score is None:
        return NO_SCORE_HEADLINE
    return _fit(f"Living Score {facts.overall.score} out of 100", HEADLINE_MAX)


def _summary(
    facts: BriefFacts,
    stored: dict[str, dict[str, Any]],
    measured: list[BriefComponent],
) -> str:
    parts: list[str] = []
    if facts.overall.score is None:
        parts.append(
            "No overall score yet: only "
            f"{facts.measured_weight} of the available component weight was measurable."
        )
    else:
        parts.append(
            f"Living Score {facts.overall.score} out of 100 over a "
            f"{facts.window_days}-day window, from {facts.measured_weight} of the "
            "measured weight."
        )

    delta = facts.overall.delta_30d if facts.overall.delta_30d is not None else facts.overall.delta_90d
    if delta is not None:
        parts.append(f"Change against the earlier snapshot: {delta:+}.")

    if measured:
        worst = measured[0]
        parts.append(
            f"Largest drag: {COMPONENT_LABELS[worst.key]} "
            f"({_lost_points(stored.get(worst.key))} points of the shortfall)."
        )

    limited = [COMPONENT_LABELS[c.key] for c in facts.components if c.status != "measured"]
    if limited:
        parts.append("Still limited data for: " + ", ".join(limited) + ".")

    return _fit(" ".join(parts), SUMMARY_MAX)


def _driver(
    component: BriefComponent, stored: dict[str, Any] | None, facts: BriefFacts
) -> BriefDriver:
    direction = _direction(facts, component.key)
    label = COMPONENT_LABELS[component.key]
    statement = (
        f"{label} scored {component.score} out of 100 and accounts for "
        f"{_lost_points(stored)} points of the shortfall, "
        f"{_DIRECTION_PHRASE[direction]}."
    )
    return BriefDriver(
        component=component.key,  # type: ignore[arg-type]
        direction=direction,  # type: ignore[arg-type]
        statement=_fit(statement, STATEMENT_MAX),
    )


def _actions(
    stored: dict[str, dict[str, Any]], measured: list[BriefComponent]
) -> list[BriefAction]:
    """The engine's own static advice, for the components it wrote advice for."""
    actions: list[BriefAction] = []
    for component in measured:
        recommendation = _recommendation(stored.get(component.key))
        if recommendation is None:
            continue
        actions.append(
            BriefAction(
                component=component.key,  # type: ignore[arg-type]
                action=_fit(recommendation, ACTION_MAX),
            )
        )
        if len(actions) == MAX_ACTIONS:
            break
    return actions


def _direction(facts: BriefFacts, key: str) -> str:
    """Which way this component moved, from the deltas already in FACTS."""
    component = next((c for c in facts.components if c.key == key), None)
    if component is None:
        return "stable"
    delta = component.delta_30d if component.delta_30d is not None else component.delta_90d
    if delta is None or delta == 0:
        return "stable"
    return "improving" if delta > 0 else "declining"


def _stored_components(snapshot: Any) -> dict[str, dict[str, Any]]:
    explanation = getattr(snapshot, "explanation", None) or {}
    raw = explanation.get("components") if isinstance(explanation, dict) else None
    if not isinstance(raw, list):
        return {}
    return {
        component["key"]: component
        for component in raw
        if isinstance(component, dict) and isinstance(component.get("key"), str)
    }


def _lost_points(stored: dict[str, Any] | None) -> Decimal:
    if not stored:
        return Decimal("0.00")
    try:
        return Decimal(str(stored.get("lost_points", "0")))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def _recommendation(stored: dict[str, Any] | None) -> str | None:
    if not stored:
        return None
    value = stored.get("recommendation")
    if isinstance(value, str) and value.strip():
        return " ".join(value.split())
    return None


def _fit(text: str, limit: int) -> str:
    """Collapse whitespace and hold the text inside its contract length."""
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."
