"""Response DTOs for the estate Living Score (BATCH 7C).

Every field here is a **projection of a stored snapshot**, never a recalculation:
the numbers, the per-component explanation, the benchmarks and the advice all come
out of the JSONB that 7B persisted when the score was calculated. That is what
makes a historical value immutable - if the estate's operations change tomorrow,
yesterday's response is byte-for-byte the same.

Nothing ORM-shaped crosses the boundary: the snapshot model is mapped field by
field, `calculated_by` stays internal (it is a user id and no part of the
contract), and the aggregate inputs are exposed only per component, where the
explanation needs them.

Scores are `Decimal`, matching the rest of the API's numeric contract, so
`0.30 * 82.76` is never a binary float.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.analytics.engine import COMPONENT_LABELS

_DTO_CONFIG = {
    "from_attributes": True,
    "populate_by_name": True,
    "serialize_by_alias": True,
}


class LivingScoreComponentResponse(BaseModel):
    """One component of a stored score, exactly as the engine described it."""

    key: str
    #: Human label, owned by the engine's vocabulary.
    label: str
    weight: Decimal
    status: str
    #: NULL means "not enough evidence for this component" - never a zero.
    score: Decimal | None
    #: The window aggregates this component consumed.
    inputs: dict[str, Any] = Field(default_factory=dict)
    benchmark: str = ""
    contribution: Decimal | None = None
    lost_points: Decimal | None = None
    explanation: str = ""
    #: Static advice, present only when the component scored poorly.
    recommendation: str | None = None

    model_config = _DTO_CONFIG


class LivingScoreSnapshotResponse(BaseModel):
    """One stored Living Score calculation, with its full breakdown."""

    snapshot_id: int = Field(..., serialization_alias="id")
    estate_id: int
    engine_version: str
    as_of: datetime
    window_start: datetime
    calculated_at: datetime
    status: str
    #: NULL when too little of the estate was measurable to justify a score.
    overall_score: Decimal | None
    measured_weight: Decimal
    #: Seeded demonstration estate: never a real customer's operations.
    is_demo: bool
    components: list[LivingScoreComponentResponse]
    #: The measured components that cost the most, worst first.
    drivers: list[LivingScoreComponentResponse]

    model_config = _DTO_CONFIG

    @classmethod
    def from_stored_snapshot(cls, snapshot, *, is_demo: bool) -> "LivingScoreSnapshotResponse":
        """Project a stored snapshot row. Never recalculates anything."""
        explanation = snapshot.explanation or {}
        return cls(
            snapshot_id=snapshot.snapshot_id,
            estate_id=snapshot.estate_id,
            engine_version=snapshot.engine_version,
            as_of=snapshot.as_of,
            window_start=snapshot.window_start,
            calculated_at=snapshot.calculated_at,
            status=snapshot.status,
            overall_score=snapshot.overall_score,
            measured_weight=snapshot.measured_weight,
            is_demo=is_demo,
            components=[
                _component_from_stored(component)
                for component in explanation.get("components", [])
            ],
            drivers=[
                _component_from_stored(component) for component in explanation.get("drivers", [])
            ],
        )


class LivingScoreHistoryRow(BaseModel):
    """A summary of one stored snapshot, for the history list.

    Deliberately small: the history is a trajectory, so it carries the date, the
    status and the number. The full breakdown is one request per snapshot away.
    """

    snapshot_id: int = Field(..., serialization_alias="id")
    as_of: datetime
    window_start: datetime
    status: str
    overall_score: Decimal | None
    measured_weight: Decimal
    engine_version: str

    model_config = _DTO_CONFIG

    @classmethod
    def from_stored_snapshot(cls, snapshot) -> "LivingScoreHistoryRow":
        return cls(
            snapshot_id=snapshot.snapshot_id,
            as_of=snapshot.as_of,
            window_start=snapshot.window_start,
            status=snapshot.status,
            overall_score=snapshot.overall_score,
            measured_weight=snapshot.measured_weight,
            engine_version=snapshot.engine_version,
        )


class LivingScoreHistoryResponse(BaseModel):
    """A page of an estate's score history, newest first."""

    count: int
    page: int
    page_size: int
    snapshots: list[LivingScoreHistoryRow]

    model_config = _DTO_CONFIG

    @classmethod
    def from_history(cls, history) -> "LivingScoreHistoryResponse":
        return cls(
            count=history.total,
            page=history.page,
            page_size=history.size,
            snapshots=[
                LivingScoreHistoryRow.from_stored_snapshot(snapshot)
                for snapshot in history.items
            ],
        )


def _component_from_stored(component: dict[str, Any]) -> LivingScoreComponentResponse:
    """Map one stored component to the wire shape.

    The stored key is ``raw_inputs``; the contract calls it ``inputs``. The label
    is looked up from the engine vocabulary rather than stored, so a label change
    is a presentation change and never a snapshot rewrite.
    """
    return LivingScoreComponentResponse(
        key=component["key"],
        label=COMPONENT_LABELS[component["key"]],
        weight=component["weight"],
        status=component["status"],
        score=component["score"],
        inputs=component.get("raw_inputs") or {},
        benchmark=component.get("benchmark") or "",
        contribution=component.get("contribution"),
        lost_points=component.get("lost_points"),
        explanation=component.get("explanation") or "",
        recommendation=component.get("recommendation"),
    )
