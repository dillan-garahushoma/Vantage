"""The only way a feature is allowed to call AI.

``GuardedLLMClient`` wraps a provider client and adds the two controls that need
persistence: a per-estate daily call budget and an append-only call ledger. It
requires an ``estate_id`` on every call, so no call can be attributed to the
wrong tenant or to nobody at all.

Failure policy (documented, deliberate):

* The budget gate **fails closed**. If the ledger cannot be read, the guard
  cannot prove the estate is under its cap, so it refuses with ``budget``. This
  is the safe direction for cost control, and it is still a clean
  ``AIUnavailableError``, so callers fall back to their non-AI path.
* Ledger **writes are best-effort**. A row that cannot be written is logged (by
  status and exception type only - never content) and the call still succeeds,
  because the provider call has already been paid for and AI is never
  load-bearing. A dropped row means the next budget count under-reports, which
  is why the failure is logged loudly.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Callable, Final, Mapping, Protocol

from app.core.ai.client import DataClass, Feature, LLMClient, LLMResult
from app.core.ai.errors import AIUnavailableError
from app.core.config import Settings

logger = logging.getLogger(__name__)

BUDGET_WINDOW: Final = timedelta(hours=24)

# Statuses that consumed a provider attempt, and therefore count against the cap.
COUNTED_STATUSES: Final[tuple[str, ...]] = ("ok", "provider_failed")

# Reasons that mean "we did reach for the provider, it just did not work".
# ``truncated`` and ``rate_limited`` belong here: the provider was called and did
# answer - with an empty envelope, or with a refusal - so the attempt is
# auditable and it is not free.
PROVIDER_FAILURE_REASONS: Final[frozenset[str]] = frozenset(
    {
        "timeout",
        "network",
        "provider_error",
        "rate_limited",
        "invalid_output",
        "truncated",
    }
)

STATUS_OK: Final = "ok"
STATUS_PROVIDER_FAILED: Final = "provider_failed"
STATUS_REJECTED_POLICY: Final = "rejected_policy"
STATUS_REJECTED_BUDGET: Final = "rejected_budget"


class CallLedger(Protocol):
    """The persistence the guard needs. Implemented by AICallEventRepository."""

    async def record(
        self,
        *,
        estate_id: int,
        feature: str,
        provider: str,
        model: str,
        status: str,
        reason: str | None = None,
        latency_ms: int | None = None,
        input_chars: int | None = None,
    ) -> None: ...

    async def count_since(
        self, *, estate_id: int, since: datetime, statuses: Sequence[str]
    ) -> int: ...


def status_for_reason(reason: str) -> str | None:
    """Map an AIUnavailableError reason to a ledger status.

    ``disabled`` returns ``None``: nothing was attempted and nothing was sent, so
    recording it would fill the ledger with noise while the layer is off. Every
    other reason is auditable.
    """
    if reason == "policy":
        return STATUS_REJECTED_POLICY
    if reason in PROVIDER_FAILURE_REASONS:
        return STATUS_PROVIDER_FAILED
    return None


class GuardedLLMClient:
    """Budget-and-ledger wrapper around a provider client."""

    def __init__(
        self,
        settings: Settings,
        inner: LLMClient,
        ledger: CallLedger | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._settings = settings
        self._inner = inner
        self._ledger = ledger
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    @property
    def inner(self) -> LLMClient:
        return self._inner

    async def generate_json(
        self,
        *,
        estate_id: int,
        system: str,
        user: str,
        schema: Mapping[str, object],
        data_class: DataClass,
        feature: Feature,
    ) -> LLMResult:
        """Run one estate-scoped AI call under the budget and ledger controls."""
        if self._ledger is not None:
            await self._enforce_budget(estate_id=estate_id, feature=feature)

        started = time.perf_counter()
        try:
            result = await self._inner.generate_json(
                system=system,
                user=user,
                schema=schema,
                data_class=data_class,
                feature=feature,
            )
        except AIUnavailableError as exc:
            status = status_for_reason(exc.reason)
            failed = status == STATUS_PROVIDER_FAILED
            await self._record(
                estate_id=estate_id,
                feature=feature,
                status=status,
                reason=exc.reason,
                latency_ms=self._elapsed_ms(started) if failed else None,
                input_chars=len(system) + len(user) if failed else None,
            )
            raise

        await self._record(
            estate_id=estate_id,
            feature=feature,
            status=STATUS_OK,
            reason=None,
            latency_ms=result.latency_ms,
            input_chars=result.input_chars,
        )
        return result

    async def _enforce_budget(self, *, estate_id: int, feature: str) -> None:
        since = self._clock() - BUDGET_WINDOW
        try:
            used = await self._ledger.count_since(  # type: ignore[union-attr]
                estate_id=estate_id, since=since, statuses=COUNTED_STATUSES
            )
        except Exception as exc:  # noqa: BLE001 - ledger failure must stay an AI failure
            logger.warning(
                "AI budget gate could not read the call ledger for estate %s (%s).",
                estate_id,
                type(exc).__name__,
            )
            raise AIUnavailableError("budget") from None

        cap = self._settings.AI_DAILY_CALL_CAP_PER_ESTATE
        if used >= cap:
            await self._record(
                estate_id=estate_id,
                feature=feature,
                status=STATUS_REJECTED_BUDGET,
                reason="budget",
            )
            raise AIUnavailableError("budget")

    async def _record(
        self,
        *,
        estate_id: int,
        feature: str,
        status: str | None,
        reason: str | None,
        latency_ms: int | None = None,
        input_chars: int | None = None,
    ) -> None:
        if status is None or self._ledger is None:
            return
        try:
            await self._ledger.record(
                estate_id=estate_id,
                feature=feature,
                provider=getattr(self._inner, "provider", "unknown"),
                model=getattr(self._inner, "model", ""),
                status=status,
                reason=reason,
                latency_ms=latency_ms,
                input_chars=input_chars,
            )
        except Exception as exc:  # noqa: BLE001 - audit write must not break the caller
            logger.warning(
                "AI call ledger write failed for estate %s (status=%s, %s).",
                estate_id,
                status,
                type(exc).__name__,
            )

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return max(0, int((time.perf_counter() - started) * 1000))
