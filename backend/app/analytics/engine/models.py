"""Frozen value objects for the Living Score engine.

Pure data: no ORM, no session, no clock. The engine never reads a row and never
writes one - the database layer aggregates rows into `EstateScoreInputs`, and
nothing else in this package knows a database exists.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

ComponentStatus = Literal["measured", "insufficient_data"]
ScoreStatus = Literal["scored", "insufficient_data"]


@dataclass(frozen=True)
class EstateScoreInputs:
    """Window aggregates for one estate, never rows.

    Every aggregate describes the same window: `[as_of - 90 days, as_of]`, both
    ends inclusive (decision D1). `as_of` must be timezone-aware, so a caller
    cannot accidentally score "now" in an unknown zone.

    Averages are `Decimal`, never `float` - the engine refuses floats so binary
    rounding cannot creep into a score that is compared and stored.
    """

    as_of: datetime
    coverage_days: int
    unit_count: int
    complaints_created: int = 0
    resolved_complaints: int = 0
    avg_resolution_days: Decimal | None = None
    work_orders_in_window: int = 0
    work_orders_completed: int = 0
    rated_count: int = 0
    avg_rating: Decimal | None = None
    provider_rating_count: int = 0
    avg_provider_rating: Decimal | None = None
    incidents: int = 0

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware.")
        for name, average in (
            ("avg_resolution_days", self.avg_resolution_days),
            ("avg_rating", self.avg_rating),
            ("avg_provider_rating", self.avg_provider_rating),
        ):
            if average is not None and not isinstance(average, Decimal):
                raise TypeError(f"{name} must be a Decimal, not {type(average).__name__}.")
        for name, count in (
            ("coverage_days", self.coverage_days),
            ("unit_count", self.unit_count),
            ("complaints_created", self.complaints_created),
            ("resolved_complaints", self.resolved_complaints),
            ("work_orders_in_window", self.work_orders_in_window),
            ("work_orders_completed", self.work_orders_completed),
            ("rated_count", self.rated_count),
            ("provider_rating_count", self.provider_rating_count),
            ("incidents", self.incidents),
        ):
            if count < 0:
                raise ValueError(f"{name} cannot be negative.")


@dataclass(frozen=True)
class ComponentResult:
    """One component's outcome, with the reasoning behind it.

    `raw_inputs` is a plain dict of the aggregates this component used, so a
    snapshot can be explained later without re-deriving anything. `score`,
    `contribution` and `lost_points` are `None` when the component has
    insufficient data - never 0, which would read as a real measurement of zero.
    """

    key: str
    weight: Decimal
    status: ComponentStatus
    score: Decimal | None
    raw_inputs: dict[str, Any] = field(default_factory=dict)
    benchmark: str = ""
    contribution: Decimal | None = None
    lost_points: Decimal | None = None
    explanation: str = ""
    recommendation: str | None = None


@dataclass(frozen=True)
class ScoreResult:
    """The whole calculation: five components, the overall score and the drivers.

    `measured_weight` is the share of the total weight that was measurable.
    `overall_score` is `None` when that share is below the D3 floor.
    `drivers` are the measured components ordered by `lost_points`, descending,
    with ties broken by the fixed component order - stable, so a client can show
    "what is dragging this estate down" without its own sorting rules.
    """

    engine_version: str
    window_start: datetime
    window_end: datetime
    overall_score: Decimal | None
    status: ScoreStatus
    measured_weight: Decimal
    components: tuple[ComponentResult, ...]
    drivers: tuple[ComponentResult, ...]
