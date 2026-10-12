"""BATCH 7A — Living Score v1.0.0 pure calculation engine.

No database, no ORM, no clock: the engine is a set of pure functions over frozen
dataclasses, so every number here is hand-computed from the documented formula in
`.agents/skills/valora-living-score/SKILL.md` and the v1.0.0 decisions D1-D6
recorded in `app/analytics/engine/constants.py`.

Written before the engine, per the batch.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.analytics.engine import (
    COMPONENT_KEYS,
    COMPONENT_WEIGHTS,
    ENGINE_VERSION,
    EstateScoreInputs,
    calculate_living_score,
    in_window,
    window_bounds,
)

ENGINE_DIR = Path(__file__).resolve().parent.parent / "app" / "analytics" / "engine"
AS_OF = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)

TWO_DP = Decimal("0.01")


def _inputs(**overrides) -> EstateScoreInputs:
    payload = {
        "as_of": AS_OF,
        "coverage_days": 90,
        "unit_count": 50,
        "complaints_created": 20,
        "resolved_complaints": 5,
        "avg_resolution_days": Decimal("6"),
        "work_orders_in_window": 8,
        "work_orders_completed": 6,
        "rated_count": 10,
        "avg_rating": Decimal("4.5"),
        "provider_rating_count": 5,
        "avg_provider_rating": Decimal("4"),
        "incidents": 3,
    }
    payload.update(overrides)
    return EstateScoreInputs(**payload)


def _component(result, key: str):
    return next(c for c in result.components if c.key == key)


# --------------------------------------------------------------------------- #
# Constants and shape
# --------------------------------------------------------------------------- #
def test_engine_version_is_one_zero_zero() -> None:
    assert ENGINE_VERSION == "1.0.0"


def test_component_keys_and_weights_match_the_authority() -> None:
    assert COMPONENT_KEYS == (
        "resolution",
        "frequency",
        "security",
        "satisfaction",
        "infrastructure",
    )
    assert COMPONENT_WEIGHTS == {
        "resolution": Decimal("0.30"),
        "frequency": Decimal("0.25"),
        "security": Decimal("0.20"),
        "satisfaction": Decimal("0.15"),
        "infrastructure": Decimal("0.10"),
    }
    assert sum(COMPONENT_WEIGHTS.values()) == Decimal("1.00")


def test_result_carries_the_window_the_version_and_five_components() -> None:
    result = calculate_living_score(_inputs())

    assert result.engine_version == "1.0.0"
    assert result.window_start == AS_OF - timedelta(days=90)
    assert result.window_end == AS_OF
    assert len(result.components) == 5
    assert [c.key for c in result.components] == list(COMPONENT_KEYS)


# --------------------------------------------------------------------------- #
# The normal case, hand-computed
# --------------------------------------------------------------------------- #
def test_normal_case_matches_the_hand_computed_numbers() -> None:
    """20 complaints over 50 units, 6-day average resolution, 4.5 average rating."""
    result = calculate_living_score(_inputs())

    assert result.status == "scored"
    assert result.measured_weight == Decimal("1.00")
    # 0.30*82.7586...+0.25*92+0.20*80+0.15*87.5+0.10*75 = 84.4525...
    assert result.overall_score == Decimal("84.45")

    assert _component(result, "resolution").score == Decimal("82.76")
    assert _component(result, "frequency").score == Decimal("92.00")
    assert _component(result, "security").score == Decimal("80.00")
    assert _component(result, "satisfaction").score == Decimal("87.50")
    assert _component(result, "infrastructure").score == Decimal("75.00")


def test_normal_case_contributions_and_lost_points() -> None:
    result = calculate_living_score(_inputs())

    resolution = _component(result, "resolution")
    assert resolution.weight == Decimal("0.30")
    assert resolution.contribution == Decimal("24.83")
    assert resolution.lost_points == Decimal("5.17")

    assert _component(result, "frequency").contribution == Decimal("23.00")
    assert _component(result, "security").lost_points == Decimal("4.00")
    assert _component(result, "satisfaction").lost_points == Decimal("1.88")
    assert _component(result, "infrastructure").lost_points == Decimal("2.50")


def test_lost_points_and_the_overall_score_add_up() -> None:
    result = calculate_living_score(_inputs())
    total_lost = sum(c.lost_points for c in result.components)

    # rounding each component to 2dp can move the total by at most a cent or two
    assert abs((Decimal("100.00") - result.overall_score) - total_lost) <= Decimal("0.05")


def test_components_report_their_raw_inputs_and_a_benchmark() -> None:
    result = calculate_living_score(_inputs())

    resolution = _component(result, "resolution")
    assert resolution.raw_inputs["avg_resolution_days"] == Decimal("6")
    assert resolution.raw_inputs["resolved_complaints"] == 5
    assert "day" in resolution.benchmark.lower()
    assert "day" in resolution.explanation.lower()

    frequency = _component(result, "frequency")
    assert frequency.raw_inputs["complaints_per_unit"] == Decimal("0.40")
    assert frequency.benchmark and frequency.explanation


def test_measured_components_are_all_measured_and_ordered_fixed() -> None:
    result = calculate_living_score(_inputs())

    assert [c.status for c in result.components] == ["measured"] * 5
    assert [c.key for c in result.drivers] == [
        "resolution",
        "security",
        "infrastructure",
        "frequency",
        "satisfaction",
    ]


# --------------------------------------------------------------------------- #
# Renormalisation (D2/D3)
# --------------------------------------------------------------------------- #
def test_overall_renormalises_over_the_measured_weights() -> None:
    """Resolution + frequency + security measured: 0.75 of the weight."""
    result = calculate_living_score(
        _inputs(
            unit_count=10,
            complaints_created=0,
            resolved_complaints=3,
            avg_resolution_days=Decimal("15.5"),
            work_orders_in_window=0,
            work_orders_completed=0,
            rated_count=0,
            avg_rating=None,
            provider_rating_count=0,
            avg_provider_rating=None,
            incidents=0,
        )
    )

    assert _component(result, "resolution").score == Decimal("50.00")
    assert _component(result, "frequency").score == Decimal("100.00")
    assert _component(result, "security").score == Decimal("100.00")
    assert _component(result, "satisfaction").status == "insufficient_data"
    assert _component(result, "infrastructure").status == "insufficient_data"

    assert result.measured_weight == Decimal("0.75")
    # (0.30*50 + 0.25*100 + 0.20*100) / 0.75 = 60 / 0.75 = 80
    assert result.overall_score == Decimal("80.00")
    assert result.status == "scored"
    # drivers are the measured components by lost points, ties in fixed key order
    assert [c.key for c in result.drivers] == ["resolution", "frequency", "security"]
    assert result.drivers[0].lost_points == Decimal("20.00")
    assert result.drivers[1].lost_points == Decimal("0.00")
    # contributions renormalise too: each is the component's share of the score
    # (0.30*50)/0.75, (0.25*100)/0.75, (0.20*100)/0.75
    assert _component(result, "resolution").contribution == Decimal("20.00")
    assert _component(result, "frequency").contribution == Decimal("33.33")
    assert _component(result, "security").contribution == Decimal("26.67")
    assert sum(c.contribution for c in result.drivers) == Decimal("80.00")
    assert sum(c.lost_points for c in result.drivers) == Decimal("20.00")


def test_below_the_measured_weight_floor_there_is_no_overall_score() -> None:
    """Resolution + satisfaction is 0.45 of the weight: not enough to score."""
    result = calculate_living_score(
        _inputs(
            coverage_days=10,
            unit_count=5,
            complaints_created=4,
            resolved_complaints=3,
            avg_resolution_days=Decimal("1"),
            work_orders_in_window=0,
            work_orders_completed=0,
            rated_count=3,
            avg_rating=Decimal("5"),
            provider_rating_count=0,
            avg_provider_rating=None,
            incidents=2,
        )
    )

    assert result.measured_weight == Decimal("0.45")
    assert result.overall_score is None
    assert result.status == "insufficient_data"
    assert [c.key for c in result.drivers] == ["resolution", "satisfaction"]


def test_above_the_measured_weight_floor_the_score_is_produced() -> None:
    """Adding the infrastructure component takes 0.45 to 0.55 and scores."""
    result = calculate_living_score(
        _inputs(
            coverage_days=10,
            unit_count=5,
            complaints_created=4,
            resolved_complaints=3,
            avg_resolution_days=Decimal("1"),
            work_orders_in_window=2,
            work_orders_completed=1,
            rated_count=3,
            avg_rating=Decimal("5"),
            provider_rating_count=0,
            avg_provider_rating=None,
            incidents=2,
        )
    )

    assert result.measured_weight == Decimal("0.55")
    # (0.30*100 + 0.15*100 + 0.10*50) / 0.55 = 50 / 0.55
    assert result.overall_score == Decimal("90.91")
    assert result.status == "scored"


# --------------------------------------------------------------------------- #
# D2 measurability
# --------------------------------------------------------------------------- #
def test_no_resolved_complaints_makes_resolution_insufficient_without_raising() -> None:
    result = calculate_living_score(
        _inputs(resolved_complaints=0, avg_resolution_days=None, complaints_created=1)
    )

    resolution = _component(result, "resolution")
    assert resolution.status == "insufficient_data"
    assert resolution.score is None
    assert resolution.contribution is None
    assert resolution.lost_points is None
    assert "3" in resolution.explanation


def test_two_resolved_complaints_is_not_enough_for_resolution() -> None:
    result = calculate_living_score(_inputs(resolved_complaints=2))

    assert _component(result, "resolution").status == "insufficient_data"


def test_three_resolved_complaints_is_enough_for_resolution() -> None:
    result = calculate_living_score(_inputs(resolved_complaints=3))

    assert _component(result, "resolution").status == "measured"


def test_zero_complaints_with_enough_coverage_scores_frequency_at_100() -> None:
    result = calculate_living_score(
        _inputs(coverage_days=30, unit_count=20, complaints_created=0)
    )

    assert _component(result, "frequency").score == Decimal("100.00")
    assert _component(result, "frequency").status == "measured"


def test_zero_complaints_with_short_coverage_is_insufficient_not_perfect() -> None:
    """A brand-new estate must not look healthy just because nothing happened yet."""
    result = calculate_living_score(
        _inputs(coverage_days=29, unit_count=20, complaints_created=0)
    )

    frequency = _component(result, "frequency")
    assert frequency.status == "insufficient_data"
    assert frequency.score is None
    assert _component(result, "security").status == "insufficient_data"


def test_a_brand_new_estate_with_no_units_is_insufficient() -> None:
    result = calculate_living_score(
        _inputs(coverage_days=90, unit_count=0, complaints_created=0)
    )

    assert _component(result, "frequency").status == "insufficient_data"
    assert _component(result, "security").status == "insufficient_data"


def test_fewer_than_three_ratings_makes_satisfaction_insufficient() -> None:
    assert (
        _component(calculate_living_score(_inputs(rated_count=2)), "satisfaction").status
        == "insufficient_data"
    )
    assert (
        _component(calculate_living_score(_inputs(rated_count=3)), "satisfaction").status
        == "measured"
    )


def test_no_work_orders_makes_infrastructure_insufficient() -> None:
    result = calculate_living_score(
        _inputs(work_orders_in_window=0, work_orders_completed=0)
    )

    assert _component(result, "infrastructure").status == "insufficient_data"
    assert _component(result, "infrastructure").score is None


# --------------------------------------------------------------------------- #
# Clamping and the documented benchmarks
# --------------------------------------------------------------------------- #
def test_resolution_benchmarks() -> None:
    assert (
        _component(
            calculate_living_score(_inputs(avg_resolution_days=Decimal("1"))), "resolution"
        ).score
        == Decimal("100.00")
    )
    assert (
        _component(
            calculate_living_score(_inputs(avg_resolution_days=Decimal("30"))), "resolution"
        ).score
        == Decimal("0.00")
    )
    assert (
        _component(
            calculate_living_score(_inputs(avg_resolution_days=Decimal("45"))), "resolution"
        ).score
        == Decimal("0.00")
    )
    assert (
        _component(
            calculate_living_score(_inputs(avg_resolution_days=Decimal("0"))), "resolution"
        ).score
        == Decimal("100.00")
    )


def test_frequency_benchmarks() -> None:
    # 0 per unit = 100, 5 or more per unit = 0
    assert (
        _component(
            calculate_living_score(_inputs(unit_count=10, complaints_created=50)), "frequency"
        ).score
        == Decimal("0.00")
    )
    assert (
        _component(
            calculate_living_score(_inputs(unit_count=10, complaints_created=100)), "frequency"
        ).score
        == Decimal("0.00")
    )
    assert (
        _component(
            calculate_living_score(_inputs(unit_count=100, complaints_created=250)), "frequency"
        ).score
        == Decimal("50.00")
    )


def test_security_benchmarks() -> None:
    assert _component(calculate_living_score(_inputs(incidents=0)), "security").score == Decimal(
        "100.00"
    )
    assert _component(calculate_living_score(_inputs(incidents=15)), "security").score == Decimal(
        "0.00"
    )
    assert _component(calculate_living_score(_inputs(incidents=60)), "security").score == Decimal(
        "0.00"
    )


def test_satisfaction_benchmarks() -> None:
    assert (
        _component(calculate_living_score(_inputs(avg_rating=Decimal("1"))), "satisfaction").score
        == Decimal("0.00")
    )
    assert (
        _component(calculate_living_score(_inputs(avg_rating=Decimal("5"))), "satisfaction").score
        == Decimal("100.00")
    )
    assert (
        _component(calculate_living_score(_inputs(avg_rating=Decimal("3"))), "satisfaction").score
        == Decimal("50.00")
    )
    # beyond the scale is clamped, not wrapped
    assert (
        _component(calculate_living_score(_inputs(avg_rating=Decimal("6"))), "satisfaction").score
        == Decimal("100.00")
    )
    assert (
        _component(calculate_living_score(_inputs(avg_rating=Decimal("0.5"))), "satisfaction").score
        == Decimal("0.00")
    )


def test_all_one_star_is_zero_and_all_five_star_is_one_hundred() -> None:
    one_star = calculate_living_score(_inputs(rated_count=12, avg_rating=Decimal("1")))
    five_star = calculate_living_score(_inputs(rated_count=12, avg_rating=Decimal("5")))

    assert _component(one_star, "satisfaction").score == Decimal("0.00")
    assert _component(five_star, "satisfaction").score == Decimal("100.00")
    assert five_star.overall_score > one_star.overall_score


def test_infrastructure_blends_completion_and_provider_rating() -> None:
    perfect = calculate_living_score(
        _inputs(
            work_orders_in_window=4,
            work_orders_completed=4,
            provider_rating_count=3,
            avg_provider_rating=Decimal("5"),
        )
    )
    worst = calculate_living_score(
        _inputs(
            work_orders_in_window=4,
            work_orders_completed=0,
            provider_rating_count=3,
            avg_provider_rating=Decimal("1"),
        )
    )

    assert _component(perfect, "infrastructure").score == Decimal("100.00")
    assert _component(worst, "infrastructure").score == Decimal("0.00")


def test_infrastructure_falls_back_to_completion_only_without_provider_data() -> None:
    result = calculate_living_score(
        _inputs(
            work_orders_in_window=4,
            work_orders_completed=2,
            provider_rating_count=0,
            avg_provider_rating=None,
        )
    )

    infrastructure = _component(result, "infrastructure")
    assert infrastructure.status == "measured"
    assert infrastructure.score == Decimal("50.00")
    assert "provider" in infrastructure.explanation.lower()
    assert "omitted" in infrastructure.explanation.lower()


# --------------------------------------------------------------------------- #
# Recommendations and explanations
# --------------------------------------------------------------------------- #
def test_a_weak_component_gets_a_static_recommendation() -> None:
    result = calculate_living_score(_inputs(incidents=12))

    security = _component(result, "security")
    assert security.score == Decimal("20.00")
    assert security.recommendation
    assert _component(result, "frequency").recommendation is None


def test_a_component_at_or_above_seventy_gets_no_recommendation() -> None:
    result = calculate_living_score(_inputs(incidents=4))  # 73.33

    security = _component(result, "security")
    assert security.score == Decimal("73.33")
    assert security.recommendation is None


def test_insufficient_components_get_no_recommendation() -> None:
    result = calculate_living_score(_inputs(rated_count=0, avg_rating=None))

    assert _component(result, "satisfaction").recommendation is None


def test_explanations_are_deterministic_strings() -> None:
    first = calculate_living_score(_inputs())
    second = calculate_living_score(_inputs())

    for component in first.components:
        counterpart = _component(second, component.key)
        assert component.explanation == counterpart.explanation
        assert component.benchmark == counterpart.benchmark
        assert component.recommendation == counterpart.recommendation


# --------------------------------------------------------------------------- #
# The window (D1)
# --------------------------------------------------------------------------- #
def test_window_bounds_are_ninety_days_inclusive() -> None:
    start, end = window_bounds(AS_OF)

    assert end == AS_OF
    assert start == AS_OF - timedelta(days=90)


def test_window_membership_boundaries() -> None:
    start, end = window_bounds(AS_OF)

    assert in_window(start, AS_OF) is True
    assert in_window(end, AS_OF) is True
    assert in_window(start + timedelta(days=45), AS_OF) is True
    assert in_window(start - timedelta(microseconds=1), AS_OF) is False
    assert in_window(end + timedelta(microseconds=1), AS_OF) is False
    assert in_window(AS_OF + timedelta(days=1), AS_OF) is False


def test_window_normalises_naive_timestamps_to_utc() -> None:
    naive = datetime(2026, 7, 12, 12, 0)
    start, _ = window_bounds(AS_OF)

    assert in_window(naive, AS_OF) is True
    assert naive.replace(tzinfo=timezone.utc) >= start


def test_the_window_does_not_read_the_clock() -> None:
    """The window is entirely a function of as_of, so the engine stays pure."""
    for offset in (timedelta(days=1), timedelta(days=3650)):
        start, end = window_bounds(AS_OF + offset)
        assert end == AS_OF + offset
        assert start == AS_OF + offset - timedelta(days=90)


# --------------------------------------------------------------------------- #
# Determinism, types and robustness
# --------------------------------------------------------------------------- #
def test_determinism_over_one_hundred_runs() -> None:
    expected = calculate_living_score(_inputs())

    for _ in range(100):
        assert calculate_living_score(_inputs()) == expected


def test_every_number_is_a_decimal() -> None:
    result = calculate_living_score(_inputs())

    assert isinstance(result.overall_score, Decimal)
    assert isinstance(result.measured_weight, Decimal)
    for component in result.components:
        assert isinstance(component.weight, Decimal)
        assert isinstance(component.score, Decimal)
        assert isinstance(component.contribution, Decimal)
        assert isinstance(component.lost_points, Decimal)


def test_the_engine_rejects_float_inputs() -> None:
    with pytest.raises(TypeError):
        EstateScoreInputs(
            as_of=AS_OF,
            coverage_days=90,
            unit_count=10,
            avg_resolution_days=6.5,  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError):
        EstateScoreInputs(
            as_of=AS_OF,
            coverage_days=90,
            unit_count=10,
            avg_rating=4.5,  # type: ignore[arg-type]
        )


def test_negative_aggregates_are_refused() -> None:
    with pytest.raises(ValueError):
        EstateScoreInputs(as_of=AS_OF, coverage_days=90, unit_count=10, incidents=-1)
    with pytest.raises(ValueError):
        EstateScoreInputs(as_of=AS_OF, coverage_days=-1, unit_count=10)


def test_a_naive_as_of_is_refused() -> None:
    with pytest.raises(ValueError):
        EstateScoreInputs(as_of=datetime(2026, 10, 10, 12, 0), coverage_days=90, unit_count=1)


def test_seeded_random_inputs_always_stay_in_range() -> None:
    rng = random.Random(20261010)

    for _ in range(250):
        inputs = EstateScoreInputs(
            as_of=AS_OF,
            coverage_days=rng.choice([0, 5, 29, 30, 45, 90, 120]),
            unit_count=rng.choice([0, 1, 7, 50, 400]),
            complaints_created=rng.randint(0, 900),
            resolved_complaints=rng.randint(0, 400),
            avg_resolution_days=(
                Decimal(rng.randint(0, 6000)) / Decimal("100")
                if rng.random() < 0.8
                else None
            ),
            work_orders_in_window=rng.randint(0, 500),
            work_orders_completed=rng.randint(0, 500),
            rated_count=rng.randint(0, 300),
            avg_rating=Decimal(rng.randint(50, 600)) / Decimal("100"),
            provider_rating_count=rng.randint(0, 100),
            avg_provider_rating=Decimal(rng.randint(0, 700)) / Decimal("100"),
            incidents=rng.randint(0, 400),
        )
        result = calculate_living_score(inputs)

        if result.overall_score is not None:
            assert Decimal("0") <= result.overall_score <= Decimal("100")
        for component in result.components:
            if component.score is not None:
                assert Decimal("0") <= component.score <= Decimal("100"), component.key


def test_extreme_inputs_do_not_overflow() -> None:
    result = calculate_living_score(
        EstateScoreInputs(
            as_of=AS_OF,
            coverage_days=100_000,
            unit_count=1,
            complaints_created=10**9,
            resolved_complaints=10**9,
            avg_resolution_days=Decimal("0"),
            work_orders_in_window=10**9,
            work_orders_completed=0,
            rated_count=10**9,
            avg_rating=Decimal("999999"),
            provider_rating_count=10**9,
            avg_provider_rating=Decimal("0"),
            incidents=10**9,
        )
    )

    assert result.overall_score is not None
    assert Decimal("0") <= result.overall_score <= Decimal("100")


def test_repeated_inputs_object_gives_identical_results() -> None:
    inputs = _inputs()
    first = calculate_living_score(inputs)
    second = calculate_living_score(inputs)

    assert first == second
    # equal in value, but a fresh immutable result object each call - no caching
    # that could hand a caller a result another caller already holds
    assert first is not second
    assert first.components is not second.components


# --------------------------------------------------------------------------- #
# The engine stays pure: no database, no ORM, no clock, no float
# --------------------------------------------------------------------------- #
def test_engine_modules_are_pure_and_dependency_free() -> None:
    sources = {
        path.name: path.read_text(encoding="utf-8") for path in sorted(ENGINE_DIR.glob("*.py"))
    }

    assert set(sources) >= {"living_score.py", "constants.py", "models.py"}
    for name, source in sources.items():
        for forbidden in (
            "sqlalchemy",
            "from app.db",
            "from app.analytics.repositories",
            "from app.analytics.models",
            "import app.",
        ):
            assert forbidden not in source, f"{name} imports {forbidden}"
        for clock in ("datetime.now", "utcnow()", "date.today", "time.time"):
            assert clock not in source, f"{name} reads the clock via {clock}"
        assert "float(" not in source, f"{name} uses float arithmetic"
