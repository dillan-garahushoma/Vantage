"""Estate Living Score v1.0.0 — a pure, deterministic calculation engine.

BATCH 7A. No database, no endpoints, no migration and no clock: the engine takes
window aggregates and returns a scored breakdown. The legacy 40/30/30
per-property score in `app/analytics/services/` is a different thing entirely and
is not touched from here.

See `constants.py` for the v1.0.0 decisions D1-D6 and
`docs/ADR-005-Living-Score-Authority.md` for why this formula is authoritative.
"""
from app.analytics.engine.constants import (
    COMPONENT_KEYS,
    COMPONENT_LABELS,
    COMPONENT_WEIGHTS,
    ENGINE_VERSION,
    MEASURED_WEIGHT_FLOOR,
    RECOMMENDATION_BELOW,
    WINDOW_DAYS,
)
from app.analytics.engine.living_score import (
    calculate_living_score,
    describe_component,
    in_window,
    window_bounds,
)
from app.analytics.engine.models import (
    ComponentResult,
    ComponentStatus,
    EstateScoreInputs,
    ScoreResult,
    ScoreStatus,
)

__all__ = [
    "COMPONENT_KEYS",
    "COMPONENT_LABELS",
    "COMPONENT_WEIGHTS",
    "ENGINE_VERSION",
    "MEASURED_WEIGHT_FLOOR",
    "RECOMMENDATION_BELOW",
    "WINDOW_DAYS",
    "ComponentResult",
    "ComponentStatus",
    "EstateScoreInputs",
    "ScoreResult",
    "ScoreStatus",
    "calculate_living_score",
    "describe_component",
    "in_window",
    "window_bounds",
]
