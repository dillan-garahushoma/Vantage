"""Living Score v1.0.0 constants and the v1.0.0 decisions.

The formula authority is the product-owner decision recorded in
`docs/ADR-005-Living-Score-Authority.md` and §8.1 of
`docs/progress/group8-vantage-reconciliation.md`: the five-component,
estate-level `v1.0.0` score over a rolling 90-day window. The legacy 40/30/30
per-property score in `app/analytics/` is **not** Living Score v1 and is not
touched by this package.

## The v1.0.0 decisions (the spec did not fix these)

Changing ANY of these is a new engine version, never an edit of an existing
snapshot: a stored snapshot records `engine_version`, and historical values must
not move when the rules move.

* **D1 — Window.** `[as_of - 90 days, as_of]`, **both ends inclusive**.
  `window_bounds()` and `in_window()` exist so the database layer can reuse the
  same definition instead of re-deriving it.
* **D2 — Measurability.** A component is measurable only when there is enough
  evidence for it to mean something:
  * resolution needs >= 3 resolved complaints;
  * frequency and security need `coverage_days >= 30` **and** `unit_count >= 1` —
    zero activity in a brand-new estate is not evidence of health;
  * satisfaction needs >= 3 ratings;
  * infrastructure needs >= 1 work order in the window.
  Otherwise the component is `insufficient_data` and contributes no weight.
* **D3 — Coverage floor.** The overall score is `None` with status
  `insufficient_data` when the measured weight is below `0.50`, so a score can
  never be built from a sliver of the estate's operations.
* **D4 — Infrastructure blend.** `0.70 * completed percentage + 0.30 * provider
  rating score`.
* **D5 — Rounding.** Components and the overall score are rounded to 2 decimal
  places with `ROUND_HALF_UP`, always computed from unrounded intermediates.
* **D6 — Security has no size normalisation.** The skill says incidents are
  "normalized by size" but gives no rule, so v1.0.0 scores the **raw estate
  incident count** against the documented 0-15 benchmark. No scaling was
  invented; sizing the benchmark is an open question for a future version.
"""
from decimal import Decimal
from typing import Final

ENGINE_VERSION: Final[str] = "1.0.0"

# Fixed order everywhere: iteration, serialisation and tie-breaking.
COMPONENT_KEYS: Final[tuple[str, ...]] = (
    "resolution",
    "frequency",
    "security",
    "satisfaction",
    "infrastructure",
)

COMPONENT_WEIGHTS: Final[dict[str, Decimal]] = {
    "resolution": Decimal("0.30"),
    "frequency": Decimal("0.25"),
    "security": Decimal("0.20"),
    "satisfaction": Decimal("0.15"),
    "infrastructure": Decimal("0.10"),
}

# D1
WINDOW_DAYS: Final[int] = 90

# D5
ROUNDING: Final[Decimal] = Decimal("0.01")

# Benchmarks, straight from the skill's normalisation table.
RESOLUTION_BEST_DAYS: Final[Decimal] = Decimal("1")
RESOLUTION_WORST_DAYS: Final[Decimal] = Decimal("30")
FREQUENCY_WORST_PER_UNIT: Final[Decimal] = Decimal("5")
SECURITY_WORST_INCIDENTS: Final[Decimal] = Decimal("15")
SATISFACTION_MIN_RATING: Final[Decimal] = Decimal("1")
SATISFACTION_MAX_RATING: Final[Decimal] = Decimal("5")

# D4
INFRASTRUCTURE_COMPLETION_WEIGHT: Final[Decimal] = Decimal("0.70")
INFRASTRUCTURE_PROVIDER_WEIGHT: Final[Decimal] = Decimal("0.30")

# D2
MIN_RESOLVED_COMPLAINTS: Final[int] = 3
MIN_COVERAGE_DAYS: Final[int] = 30
MIN_UNITS: Final[int] = 1
MIN_RATINGS: Final[int] = 3
MIN_WORK_ORDERS: Final[int] = 1

# D3
MEASURED_WEIGHT_FLOOR: Final[Decimal] = Decimal("0.50")

# A component scoring below this gets its static recommendation.
RECOMMENDATION_BELOW: Final[Decimal] = Decimal("70")

BENCHMARKS: Final[dict[str, str]] = {
    "resolution": "1 day or less scores 100; 30 days or more scores 0.",
    "frequency": "0 complaints per unit scores 100; 5 or more per unit scores 0.",
    "security": "0 incidents in the window scores 100; 15 or more scores 0.",
    "satisfaction": "1 star scores 0; 5 stars scores 100.",
    "infrastructure": (
        "Completed work orders (70%) blended with the provider rating (30%); "
        "without provider ratings, completion alone is used."
    ),
}

# Static, deterministic text. No model, no provider and no reasoning involved.
RECOMMENDATIONS: Final[dict[str, str]] = {
    "resolution": (
        "Review how long complaints take to resolve: agree a target with the team "
        "and check which categories run past it."
    ),
    "frequency": (
        "Look for repeat complaint sources: a cluster in one unit or one category "
        "usually has a single fixable cause."
    ),
    "security": (
        "Review the incidents in this window with the security contractor and "
        "address the access points that recur."
    ),
    "satisfaction": (
        "Review closed work orders that residents rated poorly with the assigned "
        "providers before the next dispatch."
    ),
    "infrastructure": (
        "Follow up the work orders that are still open or stalled, and check the "
        "completion rate per provider."
    ),
}

COMPONENT_LABELS: Final[dict[str, str]] = {
    "resolution": "Resolution speed",
    "frequency": "Complaint frequency",
    "security": "Security",
    "satisfaction": "Resident satisfaction",
    "infrastructure": "Maintenance completion",
}
