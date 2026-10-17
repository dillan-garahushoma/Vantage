"""The Living Score calculation service (BATCH 7B).

This is the only place the three pieces meet: the input repository aggregates an
estate's window, the pure engine turns those aggregates into a score, and the
snapshot repository stores the result. The engine never learns that a database
exists, and the repositories never learn what a score is.

Immutability and authorisation are both enforced here:

* **Who may measure.** An actor must be an ``hoa_admin`` **globally** *and* a
  member of that estate - ``require_role`` checks both, so a global role alone
  grants nothing. ``actor=None`` exists solely for the CLI/backfill path and is
  never reachable over HTTP: this batch adds no endpoint, and a test asserts no
  API module references this service.
* **One clock read.** ``as_of`` is resolved once, at the top, and everything after
  it (the window, the snapshot's timestamps) derives from that single value, so a
  snapshot is internally consistent and reproducible.
* **Reads never recalculate.** ``latest`` and ``history`` require estate
  membership and return stored rows; a historical value can never move.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.engine import EstateScoreInputs, ScoreResult, calculate_living_score
from app.analytics.models.living_score_snapshot import LivingScoreSnapshot
from app.analytics.repositories.living_score_inputs_repository import (
    LivingScoreInputsRepository,
)
from app.analytics.repositories.living_score_snapshot_repository import (
    LivingScoreSnapshotRepository,
)
from app.common.datetime_utils import utcnow
from app.common.enums import UserRole
from app.core.exceptions import NotFoundException
from app.identity.models.user import User
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.property.repositories.estate_repository import EstateRepository


@dataclass(frozen=True)
class SnapshotHistory:
    """One page of an estate's score history, newest first."""

    items: list[LivingScoreSnapshot]
    total: int
    page: int
    size: int


@dataclass(frozen=True)
class SnapshotView:
    """A stored snapshot plus the estate flag the API contract carries.

    ``is_demo`` belongs to the estate, not the snapshot (a snapshot is immutable
    and must not need rewriting if an estate is later reclassified), so it is read
    from the estate at response time rather than stored on the row.
    """

    snapshot: LivingScoreSnapshot
    is_demo: bool


class LivingScoreService:
    """Calculates, stores and reads the estate-level Living Score."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._snapshots = LivingScoreSnapshotRepository(db)
        self._inputs = LivingScoreInputsRepository(db)
        self._estates = EstateRepository(db)
        self._authorization = EstateAuthorizationService(db)

    async def calculate_and_snapshot(
        self,
        estate_id: int,
        actor: User | None = None,
        *,
        as_of: datetime | None = None,
    ) -> LivingScoreSnapshot:
        """Score one estate and store the immutable snapshot.

        ``actor`` must be an HOA admin globally and a member of this estate. Passing
        ``None`` is the CLI/backfill path and must never be reachable from a route.
        ``as_of`` defaults to "now", read exactly once.
        """
        if actor is None:
            # CLI/backfill only: nothing in the HTTP surface calls this service
            # (no endpoint is registered in this batch), and command-line callers
            # are already outside the request/authorisation path.
            pass
        else:
            await self._authorization.require_role(
                actor=actor,
                estate_id=estate_id,
                allowed_roles=(UserRole.hoa_admin.value,),
            )

        # Read the clock once; everything downstream derives from this value.
        effective_as_of = as_of if as_of is not None else utcnow()

        inputs = await self._inputs.gather(estate_id=estate_id, as_of=effective_as_of)
        result = calculate_living_score(inputs)
        scores = {component.key: component.score for component in result.components}

        snapshot = await self._snapshots.add(
            estate_id=estate_id,
            engine_version=result.engine_version,
            as_of=inputs.as_of,
            window_start=result.window_start,
            calculated_by=actor.user_id if actor is not None else None,
            status=result.status,
            overall_score=result.overall_score,
            measured_weight=result.measured_weight,
            resolution_score=scores["resolution"],
            frequency_score=scores["frequency"],
            security_score=scores["security"],
            satisfaction_score=scores["satisfaction"],
            infrastructure_score=scores["infrastructure"],
            inputs=_inputs_to_json(inputs),
            explanation=_result_to_json(result),
        )
        # One commit for the whole use case (AGENTS.md): the repositories flushed.
        await self._db.commit()
        return snapshot

    async def latest(self, *, estate_id: int, user: User) -> LivingScoreSnapshot | None:
        """The estate's most recent stored snapshot, or None if never scored."""
        await self._authorization.require_membership(actor=user, estate_id=estate_id)
        return await self._snapshots.latest_for_estate(estate_id=estate_id)

    async def latest_view(self, *, estate_id: int, user: User) -> SnapshotView | None:
        """The latest snapshot as the API needs it: one authorization, one read.

        Returns None when the estate has never been scored, which the route turns
        into a 404 rather than an empty score.
        """
        snapshot = await self.latest(estate_id=estate_id, user=user)
        if snapshot is None:
            return None
        return SnapshotView(snapshot=snapshot, is_demo=await self._is_demo(estate_id))

    async def recalculate_view(
        self,
        *,
        estate_id: int,
        admin: User,
        as_of: datetime | None = None,
    ) -> SnapshotView:
        """Calculate, store and shape a new snapshot for an HOA admin."""
        snapshot = await self.calculate_and_snapshot(estate_id, actor=admin, as_of=as_of)
        return SnapshotView(snapshot=snapshot, is_demo=await self._is_demo(estate_id))

    async def recalculate_estates(
        self,
        *,
        estate_id: int | None = None,
        include_demo: bool = False,
    ) -> list[LivingScoreSnapshot]:
        """Score every selected estate without an actor. The scheduled-job path.

        Real estates only unless ``include_demo`` is set: a seeded demonstration
        estate is not a customer's operations and must not be swept by default.
        One snapshot per estate, committed per estate; no queue and no scheduler
        here - the caller (a Windows Task Scheduler job) decides the cadence.
        """
        estate_ids = await self._estates.list_ids_for_scoring(
            estate_id=estate_id, include_demo=include_demo
        )
        scored: list[LivingScoreSnapshot] = []
        for one_estate_id in estate_ids:
            scored.append(await self.calculate_and_snapshot(one_estate_id, actor=None))
        return scored

    async def _is_demo(self, estate_id: int) -> bool:
        """Read the estate flag. Private: a route must authorize before asking."""
        estate = await self._estates.get_by_id(estate_id)
        if estate is None:
            raise NotFoundException(f"Estate with id {estate_id} was not found.")
        return bool(estate.is_demo)

    async def history(
        self, *, estate_id: int, user: User, page: int, size: int
    ) -> SnapshotHistory:
        """One page of the estate's score history, newest first. Never recalculated."""
        await self._authorization.require_membership(actor=user, estate_id=estate_id)
        items = await self._snapshots.history(
            estate_id=estate_id,
            offset=(page - 1) * size,
            limit=size,
        )
        total = await self._snapshots.count(estate_id=estate_id)
        return SnapshotHistory(items=list(items), total=total, page=page, size=size)


# --------------------------------------------------------------------------- #
# JSON shaping. Snapshots must stay explainable: store the exact inputs and the
# engine's own reasoning, with Decimals as strings so no precision is lost.
# --------------------------------------------------------------------------- #
def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _inputs_to_json(inputs: EstateScoreInputs) -> dict[str, Any]:
    """The window aggregates the engine consumed, in a JSON-safe form."""
    return _json_safe(asdict(inputs))


def _result_to_json(result: ScoreResult) -> dict[str, Any]:
    """The engine's full reasoning: components, benchmarks, drivers, advice."""
    return _json_safe(
        {
            "engine_version": result.engine_version,
            "window_start": result.window_start,
            "window_end": result.window_end,
            "status": result.status,
            "overall_score": result.overall_score,
            "measured_weight": result.measured_weight,
            "components": [asdict(component) for component in result.components],
            "drivers": [asdict(component) for component in result.drivers],
        }
    )
