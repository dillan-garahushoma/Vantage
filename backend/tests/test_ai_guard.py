"""Tests for the per-estate AI budget guard and the call ledger (BATCH AI-2).

No database and no network: the ledger is an in-memory fake and the provider is a
stub, so these tests pin the guard's behaviour without either dependency.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from app.core.ai.client import DataClass, GatedLLMClient, LLMResult
from app.core.ai.errors import AIUnavailableError
from app.core.ai.guard import GuardedLLMClient
from app.core.config import Settings

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
}

T0 = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


def make_settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "ENVIRONMENT": "test",
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/valora_test",
        "SECRET_KEY": "test-secret-not-for-production-0123456789",
        "AI_ENABLED": True,
        "AI_INSIGHTS_ENABLED": True,
        "AI_TRIAGE_ENABLED": True,
        "AI_PERSONAL_DATA_ALLOWED": False,
        "AI_PROVIDER": "fake",
        "AI_MODEL": "fake-model",
        "AI_TIMEOUT_SECONDS": 15.0,
        "AI_MAX_INPUT_CHARS": 6000,
        "AI_MAX_OUTPUT_TOKENS": 600,
        "AI_DAILY_CALL_CAP_PER_ESTATE": 2,
    }
    base.update(overrides)
    return Settings(**base)


class StubClient:
    """A provider stub that either succeeds or raises a chosen reason."""

    provider = "stub"
    model = "stub-model"

    def __init__(self, *, reason: str | None = None, latency_ms: int = 7) -> None:
        self.reason = reason
        self.latency_ms = latency_ms
        self.calls = 0

    async def generate_json(
        self, *, system: str, user: str, schema: Any, data_class: Any, feature: str
    ) -> LLMResult:
        self.calls += 1
        if self.reason is not None:
            raise AIUnavailableError(self.reason)
        return LLMResult(
            parsed={"ok": True},
            provider=self.provider,
            model=self.model,
            latency_ms=self.latency_ms,
            input_chars=len(system) + len(user),
        )


class FakeLedger:
    """In-memory stand-in for AICallEventRepository with an injectable clock."""

    def __init__(self, clock=None) -> None:
        self._clock = clock or (lambda: T0)
        self.rows: list[dict[str, Any]] = []

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
    ) -> None:
        self.rows.append(
            {
                "estate_id": estate_id,
                "feature": feature,
                "provider": provider,
                "model": model,
                "status": status,
                "reason": reason,
                "latency_ms": latency_ms,
                "input_chars": input_chars,
                "created_at": self._clock(),
            }
        )

    async def count_since(
        self, *, estate_id: int, since: datetime, statuses: Any
    ) -> int:
        wanted = set(statuses)
        return sum(
            1
            for row in self.rows
            if row["estate_id"] == estate_id
            and row["status"] in wanted
            and row["created_at"] >= since
        )


def make_guard(
    *,
    ledger: FakeLedger,
    inner: Any = None,
    settings: Settings | None = None,
    clock=None,
) -> GuardedLLMClient:
    cfg = settings if settings is not None else make_settings()
    provider = inner if inner is not None else StubClient()
    gated = GatedLLMClient(cfg, provider)
    # The fake ledger stamps its rows with its own clock. The guard must read the
    # SAME clock, or its 24h window drifts away from the stored timestamps as
    # real time advances and the cap silently stops binding. Default both to T0.
    if clock is None:
        clock = lambda: T0  # noqa: E731 - a tiny injectable clock, not a def
    return GuardedLLMClient(cfg, gated, ledger, clock=clock)


async def call(guard: GuardedLLMClient, *, estate_id: int = 1, **overrides: Any) -> LLMResult:
    kwargs: dict[str, Any] = {
        "estate_id": estate_id,
        "system": "system",
        "user": "user",
        "schema": SCHEMA,
        "data_class": DataClass.aggregate,
        "feature": "insights",
    }
    kwargs.update(overrides)
    return await guard.generate_json(**kwargs)


# ------------------------------------------------------------------- budget cap


@pytest.mark.asyncio
async def test_budget_cap_blocks_the_call_after_the_cap_and_records_it() -> None:
    ledger = FakeLedger()
    guard = make_guard(ledger=ledger)

    assert (await call(guard)).parsed == {"ok": True}
    assert (await call(guard)).parsed == {"ok": True}

    with pytest.raises(AIUnavailableError) as exc:
        await call(guard)

    assert exc.value.reason == "budget"
    assert [row["status"] for row in ledger.rows] == [
        "ok",
        "ok",
        "rejected_budget",
    ]
    assert ledger.rows[-1]["reason"] == "budget"
    # A rejected call never carries content metadata.
    assert ledger.rows[-1]["latency_ms"] is None
    assert ledger.rows[-1]["input_chars"] is None


@pytest.mark.asyncio
async def test_provider_failures_count_toward_the_cap() -> None:
    ledger = FakeLedger()
    stub = StubClient(reason="provider_error")
    guard = make_guard(ledger=ledger, inner=stub)

    for _ in range(2):
        with pytest.raises(AIUnavailableError) as exc:
            await call(guard)
        assert exc.value.reason == "provider_error"

    # Both failures consumed the estate's budget.
    with pytest.raises(AIUnavailableError) as exc:
        await call(guard)
    assert exc.value.reason == "budget"

    assert [row["status"] for row in ledger.rows] == [
        "provider_failed",
        "provider_failed",
        "rejected_budget",
    ]
    assert stub.calls == 2


@pytest.mark.asyncio
async def test_policy_rejections_are_recorded_but_do_not_consume_budget() -> None:
    ledger = FakeLedger()
    stub = StubClient()
    guard = make_guard(ledger=ledger, inner=stub)

    with pytest.raises(AIUnavailableError) as exc:
        await call(guard, data_class=DataClass.personal)
    assert exc.value.reason == "policy"

    # The cap is 2; two rejected_policy rows must not block the real calls.
    assert (await call(guard)).parsed == {"ok": True}
    assert (await call(guard)).parsed == {"ok": True}

    assert [row["status"] for row in ledger.rows] == [
        "rejected_policy",
        "ok",
        "ok",
    ]
    assert ledger.rows[0]["reason"] == "policy"


@pytest.mark.asyncio
async def test_disabled_calls_are_not_recorded_at_all() -> None:
    """With AI off nothing happened, so the ledger stays empty."""
    ledger = FakeLedger()
    settings = make_settings(AI_ENABLED=False)
    guard = make_guard(ledger=ledger, settings=settings)

    with pytest.raises(AIUnavailableError) as exc:
        await call(guard)

    assert exc.value.reason == "disabled"
    assert ledger.rows == []


@pytest.mark.asyncio
async def test_estate_budgets_are_isolated() -> None:
    ledger = FakeLedger()
    guard = make_guard(ledger=ledger)

    await call(guard, estate_id=1)
    await call(guard, estate_id=1)

    # Estate 1 is at its cap...
    with pytest.raises(AIUnavailableError) as exc:
        await call(guard, estate_id=1)
    assert exc.value.reason == "budget"

    # ...but estate 2 is untouched.
    assert (await call(guard, estate_id=2)).parsed == {"ok": True}


@pytest.mark.asyncio
async def test_count_window_is_the_last_twenty_four_hours() -> None:
    ledger = FakeLedger()
    # A row from 25 hours ago must not count against the cap.
    ledger.rows.append(
        {
            "estate_id": 1,
            "feature": "insights",
            "provider": "stub",
            "model": "stub-model",
            "status": "ok",
            "reason": None,
            "latency_ms": 1,
            "input_chars": 1,
            "created_at": T0 - timedelta(hours=25),
        }
    )
    settings = make_settings(AI_DAILY_CALL_CAP_PER_ESTATE=1)
    guard = make_guard(ledger=ledger, settings=settings)

    assert (await call(guard)).parsed == {"ok": True}

    with pytest.raises(AIUnavailableError) as exc:
        await call(guard)
    assert exc.value.reason == "budget"


# ------------------------------------------------------------------ ledger rows


@pytest.mark.asyncio
async def test_ok_row_records_only_metadata() -> None:
    ledger = FakeLedger()
    guard = make_guard(ledger=ledger)

    await call(guard, estate_id=7, system="aaaa", user="bb")

    row = ledger.rows[0]
    assert set(row) == {
        "estate_id",
        "feature",
        "provider",
        "model",
        "status",
        "reason",
        "latency_ms",
        "input_chars",
        "created_at",
    }
    assert row["estate_id"] == 7
    assert row["feature"] == "insights"
    assert row["provider"] == "stub"
    assert row["model"] == "stub-model"
    assert row["status"] == "ok"
    assert row["reason"] is None
    assert row["latency_ms"] == 7
    assert row["input_chars"] == 6


@pytest.mark.asyncio
async def test_rejection_rows_still_identify_the_provider() -> None:
    ledger = FakeLedger()
    settings = make_settings(AI_PERSONAL_DATA_ALLOWED=False)
    guard = make_guard(ledger=ledger, settings=settings)

    with pytest.raises(AIUnavailableError):
        await call(guard, data_class=DataClass.personal)

    # All the columns are NOT NULL in the schema, so a rejection row must still
    # carry a provider and a model string.
    assert ledger.rows[0]["provider"] == "stub"
    assert ledger.rows[0]["model"] == "stub-model"


# ------------------------------------------------------------------ guard shape


@pytest.mark.asyncio
async def test_estate_id_is_required() -> None:
    ledger = FakeLedger()
    guard = make_guard(ledger=ledger)

    with pytest.raises(TypeError):
        await guard.generate_json(  # type: ignore[call-arg]
            system="s",
            user="u",
            schema=SCHEMA,
            data_class=DataClass.aggregate,
            feature="insights",
        )

    assert ledger.rows == []


@pytest.mark.asyncio
async def test_a_ledger_write_failure_never_breaks_the_caller() -> None:
    """AI is never load-bearing: a ledger outage must not fail a good result."""

    class BrokenLedger(FakeLedger):
        async def record(self, **kwargs: Any) -> None:  # type: ignore[override]
            raise RuntimeError("ledger is down")

    guard = make_guard(ledger=BrokenLedger())

    assert (await call(guard)).parsed == {"ok": True}


@pytest.mark.asyncio
async def test_a_ledger_read_failure_fails_closed_on_the_budget() -> None:
    """If the cap cannot be verified, the call is refused (safe direction)."""

    class BrokenLedger(FakeLedger):
        async def count_since(self, **kwargs: Any) -> int:  # type: ignore[override]
            raise RuntimeError("ledger is down")

    stub = StubClient()
    guard = make_guard(ledger=BrokenLedger(), inner=stub)

    with pytest.raises(AIUnavailableError) as exc:
        await call(guard)

    assert exc.value.reason == "budget"
    assert stub.calls == 0


@pytest.mark.asyncio
async def test_guard_reports_the_inner_provider_and_model() -> None:
    gated = GatedLLMClient(make_settings(), StubClient())
    assert gated.provider == "stub"
    assert gated.model == "stub-model"

    off = GatedLLMClient(make_settings(AI_ENABLED=False), None)
    assert off.provider == "disabled"


@pytest.mark.asyncio
async def test_every_provider_failure_reason_counts_as_a_failed_call() -> None:
    for reason in ("timeout", "network", "provider_error", "invalid_output"):
        ledger = FakeLedger()
        guard = make_guard(ledger=ledger, inner=StubClient(reason=reason))
        with pytest.raises(AIUnavailableError):
            await call(guard)
        assert ledger.rows[0]["status"] == "provider_failed", reason
        assert ledger.rows[0]["reason"] == reason
        assert ledger.rows[0]["latency_ms"] is not None
        assert ledger.rows[0]["input_chars"] == len("system") + len("user")
