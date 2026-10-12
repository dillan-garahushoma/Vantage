"""BriefFacts, the grounding validator and the template brief (BATCH AI-4).

No database, no network. The fixtures are built in the **stored** JSON shape that
7B writes (Decimals serialised as strings, free text in `benchmark`,
`explanation` and `recommendation`), so these tests prove the facts carry numbers
only and that the template is rebuilt from what is actually on the row.

Written before the implementation, per the batch.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.analytics.ai.brief_facts import (
    COMPONENT_KEYS,
    BriefFacts,
    build_brief_facts,
)
from app.analytics.ai.brief_output import (
    PROMPT_VERSION,
    BriefOutput,
    build_user_prompt,
    brief_output_schema,
)
from app.analytics.ai.grounding import GroundingViolation, validate_grounding
from app.analytics.ai.template import build_template_brief

AS_OF = datetime(2026, 10, 11, 9, 0, tzinfo=timezone.utc)

# The engine's own free text, with a marker so a leak is unmistakable.
BENCHMARK_TEXT = "1 day or less scores 100; 30 days or more scores 0."
EXPLANATION_TEXT = "MARKER-ENGINE-PROSE 3 complaints resolved, averaging 1.33 days."
RECOMMENDATION_TEXT = "MARKER-ADVICE Review how long complaints take to resolve."
PERSONAL_MARKER = "Thandi van der Merwe lives at unit A-101 and emailed residents@example.com"

COMPONENT_INPUTS: dict[str, dict] = {
    "resolution": {"avg_resolution_days": "1.33", "resolved_complaints": 3},
    "frequency": {
        "complaints_created": 4,
        "unit_count": 2,
        "coverage_days": 90,
        "complaints_per_unit": "2.00",
    },
    "security": {"incidents": 1, "coverage_days": 90, "unit_count": 2},
    "satisfaction": {"avg_rating": "4.33", "rated_count": 3},
    "infrastructure": {
        "work_orders_in_window": 4,
        "work_orders_completed": 3,
        "avg_provider_rating": "4.00",
        "provider_rating_count": 1,
    },
}

COMPONENT_SCORES: dict[str, str | None] = {
    "resolution": "98.85",
    "frequency": "60.00",
    "security": "93.33",
    "satisfaction": "83.33",
    "infrastructure": "75.00",
}

WEIGHTS = {
    "resolution": "0.30",
    "frequency": "0.25",
    "security": "0.20",
    "satisfaction": "0.15",
    "infrastructure": "0.10",
}

LOST_POINTS = {
    "frequency": "10.00",
    "satisfaction": "2.50",
    "infrastructure": "2.50",
    "security": "1.33",
    "resolution": "0.34",
}


def _component(key: str, *, score: str | None = None, status: str = "measured") -> dict:
    if score is None:
        score = COMPONENT_SCORES[key]
    if status == "insufficient_data":
        score = None
    return {
        "key": key,
        "weight": WEIGHTS[key],
        "status": status,
        "score": score,
        "raw_inputs": COMPONENT_INPUTS[key],
        "benchmark": BENCHMARK_TEXT,
        "contribution": "0.00" if score is None else "10.00",
        "lost_points": "0.00" if score is None else LOST_POINTS.get(key, "1.00"),
        "explanation": EXPLANATION_TEXT,
        "recommendation": RECOMMENDATION_TEXT if key == "frequency" else None,
    }


def stored_snapshot(
    *,
    as_of: datetime = AS_OF,
    snapshot_id: int = 11,
    status: str = "scored",
    overall_score: str | None = "83.32",
    measured_weight: str = "1.00",
    insufficient: tuple[str, ...] = (),
    is_demo: bool = False,
) -> SimpleNamespace:
    """One snapshot row in the shape 7B stores, plus the estate flag."""
    components = [
        _component(key, status="insufficient_data" if key in insufficient else "measured")
        for key in COMPONENT_KEYS
    ]
    drivers = sorted(
        (c for c in components if c["status"] == "measured"),
        key=lambda c: Decimal(c["lost_points"]),
        reverse=True,
    )
    explanation = {
        "engine_version": "1.0.0",
        "window_start": (as_of - timedelta(days=90)).isoformat(),
        "window_end": as_of.isoformat(),
        "status": status,
        "overall_score": overall_score,
        "measured_weight": measured_weight,
        "components": components,
        "drivers": drivers,
    }
    inputs = {
        "as_of": as_of.isoformat(),
        "coverage_days": 90,
        "unit_count": 2,
        "complaints_created": 4,
        "resolved_complaints": 3,
        "avg_resolution_days": "1.33",
        "work_orders_in_window": 4,
        "work_orders_completed": 3,
        "rated_count": 3,
        "avg_rating": "4.33",
        "provider_rating_count": 1,
        "avg_provider_rating": "4.00",
        "incidents": 1,
    }
    return SimpleNamespace(
        snapshot_id=snapshot_id,
        estate_id=7,
        engine_version="1.0.0",
        as_of=as_of,
        window_start=as_of - timedelta(days=90),
        calculated_at=as_of + timedelta(minutes=1),
        status=status,
        overall_score=None if overall_score is None else Decimal(overall_score),
        measured_weight=Decimal(measured_weight),
        resolution_score=None if "resolution" in insufficient else Decimal("98.85"),
        frequency_score=None if "frequency" in insufficient else Decimal("60.00"),
        security_score=None if "security" in insufficient else Decimal("93.33"),
        satisfaction_score=None if "satisfaction" in insufficient else Decimal("83.33"),
        infrastructure_score=None if "infrastructure" in insufficient else Decimal("75.00"),
        inputs=inputs,
        explanation=explanation,
        is_demo=is_demo,
    )


# ---------------------------------------------------------------- the facts


def test_facts_carry_the_engine_version_window_and_comparison_lookbacks() -> None:
    facts = build_brief_facts(stored_snapshot())

    assert isinstance(facts, BriefFacts)
    assert facts.engine_version == "1.0.0"
    assert facts.window_days == 90
    assert facts.compared_days == (30, 90)
    assert facts.as_of == AS_OF


def test_facts_cover_the_five_engine_components_in_engine_order() -> None:
    facts = build_brief_facts(stored_snapshot())

    assert [component.key for component in facts.components] == list(COMPONENT_KEYS)
    assert len(facts.components) == 5
    assert facts.overall.score == Decimal("83.32")
    assert facts.overall.status == "scored"
    assert facts.measured_weight == Decimal("1.00")
    frequency = next(c for c in facts.components if c.key == "frequency")
    assert frequency.weight_pct == Decimal("25.00")
    assert frequency.score == Decimal("60.00")
    assert frequency.status == "measured"


def test_component_inputs_keep_their_numbers_as_numbers() -> None:
    facts = build_brief_facts(stored_snapshot())

    frequency = next(c for c in facts.components if c.key == "frequency")
    assert frequency.inputs["complaints_created"] == 4
    assert frequency.inputs["complaints_per_unit"] == Decimal("2.00")
    assert frequency.inputs["coverage_days"] == 90


def test_facts_contain_no_free_text_at_all() -> None:
    """The stored row is full of prose; none of it may reach the facts."""

    facts = build_brief_facts(stored_snapshot())
    dumped = facts.model_dump_json()

    for marker in (BENCHMARK_TEXT, EXPLANATION_TEXT, RECOMMENDATION_TEXT):
        assert marker not in dumped
    # No field is a string except the version and the status vocabulary.
    for name, field in BriefFacts.model_fields.items():
        annotation = str(field.annotation)
        if name in {"engine_version", "overall", "components"}:
            continue
        assert "str" not in annotation or "Literal" in annotation, (name, annotation)


def test_every_input_value_is_a_number_or_null() -> None:
    facts = build_brief_facts(stored_snapshot())

    for component in facts.components:
        for name, value in component.inputs.items():
            assert isinstance(value, (int, Decimal)) or value is None, (name, value)
            assert not isinstance(value, bool)


def test_free_text_in_a_stored_input_is_refused_not_coerced() -> None:
    """A prompt-injection payload cannot ride in through the stored inputs."""
    snapshot = stored_snapshot()
    snapshot.explanation["components"][0]["raw_inputs"] = {"note": PERSONAL_MARKER}

    with pytest.raises(ValueError):
        build_brief_facts(snapshot)


def test_identical_snapshots_produce_identical_facts() -> None:
    first = build_brief_facts(stored_snapshot())
    second = build_brief_facts(stored_snapshot())

    assert first.model_dump() == second.model_dump()


def test_deltas_are_null_without_a_previous_snapshot() -> None:
    facts = build_brief_facts(stored_snapshot(), None, None)

    assert facts.overall.delta_30d is None
    assert facts.overall.delta_30d_abs is None
    assert facts.overall.delta_90d is None
    for component in facts.components:
        assert component.delta_30d is None
        assert component.delta_30d_abs is None
        assert component.delta_90d is None
        assert component.delta_90d_abs is None


def test_deltas_are_computed_here_from_the_stored_previous_snapshots() -> None:
    previous_30 = stored_snapshot(
        as_of=AS_OF - timedelta(days=30), snapshot_id=10, overall_score="84.45"
    )
    previous_90 = stored_snapshot(
        as_of=AS_OF - timedelta(days=90), snapshot_id=9, overall_score="80.00"
    )

    facts = build_brief_facts(stored_snapshot(), previous_30, previous_90)

    assert facts.overall.delta_30d == Decimal("-1.13")
    assert facts.overall.delta_30d_abs == Decimal("1.13")
    assert facts.overall.delta_90d == Decimal("3.32")
    assert facts.overall.delta_90d_abs == Decimal("3.32")


def test_a_component_delta_is_null_when_the_previous_component_had_no_score() -> None:
    still_early = stored_snapshot(
        as_of=AS_OF - timedelta(days=30),
        snapshot_id=10,
        status="insufficient_data",
        overall_score=None,
        measured_weight="0.10",
        insufficient=("frequency",),
    )

    facts = build_brief_facts(stored_snapshot(), still_early, None)

    frequency = next(c for c in facts.components if c.key == "frequency")
    resolution = next(c for c in facts.components if c.key == "resolution")
    assert frequency.delta_30d is None
    assert resolution.delta_30d == Decimal("0.00")
    assert facts.overall.delta_30d is None


# ------------------------------------------------------------ the validator


def make_output(**overrides) -> BriefOutput:
    base = {
        "headline": "Living Score 83.32 out of 100",
        "summary": "The estate scored 83.32 over 90 days, with complaint frequency at 60.00.",
        "drivers": [
            {
                "component": "frequency",
                "direction": "declining",
                "statement": "Complaint frequency scored 60.00 and lost 10.00 points.",
            }
        ],
        "actions": [
            {"component": "frequency", "action": RECOMMENDATION_TEXT},
        ],
    }
    base.update(overrides)
    return BriefOutput(**base)


def grounded_facts() -> BriefFacts:
    previous_30 = stored_snapshot(
        as_of=AS_OF - timedelta(days=30), snapshot_id=10, overall_score="84.45"
    )
    return build_brief_facts(stored_snapshot(), previous_30, None)


def test_a_faithful_output_passes_the_validator() -> None:
    validate_grounding(make_output(), grounded_facts())


@pytest.mark.parametrize(
    "number",
    ["83.32", "83.3", "83", "60.00", "60.0", "60", "90", "2.00", "2.0", "4", "30", "100", "0"],
)
def test_numbers_at_every_allowed_rounding_pass(number: str) -> None:
    output = make_output(summary=f"The figure {number} comes straight out of the facts.")

    validate_grounding(output, grounded_facts())


def test_the_absolute_value_of_a_negative_delta_is_accepted() -> None:
    facts = grounded_facts()
    assert facts.overall.delta_30d == Decimal("-1.13")

    output = make_output(headline="Living Score 83.32, down 1.13 over 30 days")

    validate_grounding(output, facts)


def test_an_invented_number_is_rejected() -> None:
    output = make_output(summary="The estate scored 77.40 this window.")

    with pytest.raises(GroundingViolation):
        validate_grounding(output, grounded_facts())


def test_a_number_in_a_different_unit_is_rejected() -> None:
    """0.30 is not 30.00: a weight percentage may not become a fraction."""
    facts = grounded_facts()
    frequency = next(c for c in facts.components if c.key == "frequency")
    assert frequency.weight_pct == Decimal("25.00")

    output = make_output(summary="Complaint frequency carries a weight of 0.25.")

    with pytest.raises(GroundingViolation):
        validate_grounding(output, facts)


def test_a_number_inside_a_driver_statement_is_checked_too() -> None:
    output = make_output(
        drivers=[
            {
                "component": "frequency",
                "direction": "stable",
                "statement": "Frequency held at 60.00 with 42 complaints this window.",
            }
        ]
    )

    with pytest.raises(GroundingViolation):
        validate_grounding(output, grounded_facts())


def test_a_number_inside_an_action_is_checked_too() -> None:
    output = make_output(
        actions=[{"component": "frequency", "action": "Cut complaints by 77 percent."}]
    )

    with pytest.raises(GroundingViolation):
        validate_grounding(output, grounded_facts())


def test_an_unknown_component_is_rejected() -> None:
    """Bypassing pydantic proves the validator itself enforces the enum."""
    output = BriefOutput.model_construct(
        headline="Living Score 83.32 out of 100",
        summary="Fine.",
        drivers=[
            BriefOutput.model_fields["drivers"].annotation.__args__[0].model_construct(
                component="roofing", direction="stable", statement="Roofing is fine."
            )
        ],
        actions=[],
    )

    with pytest.raises(GroundingViolation):
        validate_grounding(output, grounded_facts())


def test_the_output_model_itself_refuses_an_unknown_component() -> None:
    with pytest.raises(ValidationError):
        make_output(drivers=[{"component": "roofing", "direction": "stable", "statement": "x"}])


def test_the_output_model_enforces_the_documented_lengths() -> None:
    assert make_output().headline
    with pytest.raises(ValidationError):
        make_output(headline="x" * 121)
    with pytest.raises(ValidationError):
        make_output(summary="x" * 601)
    with pytest.raises(ValidationError):
        make_output(
            drivers=[
                {"component": "frequency", "direction": "stable", "statement": "x" * 201}
            ]
        )
    with pytest.raises(ValidationError):
        make_output(actions=[{"component": "frequency", "action": "x" * 201}])


def test_the_output_model_allows_at_most_three_drivers_and_actions() -> None:
    keys = ["resolution", "frequency", "security", "satisfaction"]
    with pytest.raises(ValidationError):
        make_output(
            drivers=[
                {"component": key, "direction": "stable", "statement": "steady"}
                for key in keys
            ]
        )
    with pytest.raises(ValidationError):
        make_output(
            actions=[{"component": key, "action": "keep going"} for key in keys]
        )


def test_the_output_model_refuses_extra_fields_and_bad_directions() -> None:
    with pytest.raises(ValidationError):
        make_output(verdict="excellent")
    with pytest.raises(ValidationError):
        make_output(
            drivers=[
                {"component": "frequency", "direction": "worsening", "statement": "x"}
            ]
        )


# ---------------------------------------------------------------- the prompt


def test_the_prompt_version_and_schema_are_fixed() -> None:
    assert PROMPT_VERSION == "brief-v1"

    schema = brief_output_schema()
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"headline", "summary", "drivers", "actions"}
    assert schema["properties"]["drivers"]["items"]["properties"]["component"]["enum"] == list(
        COMPONENT_KEYS
    )
    assert schema["properties"]["drivers"]["items"]["properties"]["direction"]["enum"] == [
        "improving",
        "declining",
        "stable",
    ]
    assert schema["properties"]["actions"]["items"]["properties"]["component"]["enum"] == list(
        COMPONENT_KEYS
    )


def test_the_schema_is_a_fresh_object_every_call() -> None:
    first = brief_output_schema()
    first["properties"]["headline"]["enum"] = ["injected"]

    assert "enum" not in brief_output_schema()["properties"]["headline"]


def test_the_user_prompt_carries_the_facts_and_nothing_personal() -> None:
    facts = grounded_facts()

    prompt = build_user_prompt(facts)

    assert "83.32" in prompt
    assert "frequency" in prompt
    for forbidden in ("Alice", "@", "unit A-101", PERSONAL_MARKER, "complaint text"):
        assert forbidden not in prompt, forbidden


# -------------------------------------------------------------- the template


def test_the_template_has_the_output_shape_and_is_ai_free() -> None:
    snapshot = stored_snapshot()

    template = build_template_brief(snapshot, build_brief_facts(snapshot))

    assert isinstance(template, BriefOutput)
    assert len(template.headline) <= 120
    assert len(template.summary) <= 600
    assert 1 <= len(template.drivers) <= 3
    assert all(len(driver.statement) <= 200 for driver in template.drivers)
    assert all(len(action.action) <= 200 for action in template.actions)


def test_the_template_is_rebuilt_deterministically_every_time() -> None:
    snapshot = stored_snapshot()
    facts = build_brief_facts(snapshot)

    assert (
        build_template_brief(snapshot, facts).model_dump()
        == build_template_brief(snapshot, facts).model_dump()
    )


def test_the_template_names_the_score_and_the_biggest_drag() -> None:
    snapshot = stored_snapshot()

    template = build_template_brief(snapshot, build_brief_facts(snapshot))

    assert "83.32" in template.headline
    assert template.drivers[0].component == "frequency"
    assert "frequency" in template.drivers[0].statement.lower()
    assert [driver.component for driver in template.drivers] == [
        "frequency",
        "satisfaction",
        "infrastructure",
    ]


def test_the_template_uses_the_stored_advice_for_its_actions() -> None:
    snapshot = stored_snapshot()

    template = build_template_brief(snapshot, build_brief_facts(snapshot))

    assert [action.component for action in template.actions] == ["frequency"]
    assert template.actions[0].action == RECOMMENDATION_TEXT


def test_the_template_refuses_to_invent_a_score_when_there_is_none() -> None:
    snapshot = stored_snapshot(
        status="insufficient_data",
        overall_score=None,
        measured_weight="0.10",
        insufficient=("frequency", "security", "satisfaction", "infrastructure"),
    )

    template = build_template_brief(snapshot, build_brief_facts(snapshot))

    assert "83.32" not in template.headline
    assert "83.32" not in template.summary
    # Only resolution had evidence, so it is the only driver - and no overall
    # score is invented to sit above it.
    assert [driver.component for driver in template.drivers] == ["resolution"]
    assert template.actions == []


def test_the_template_says_a_component_is_still_limited_in_data() -> None:
    snapshot = stored_snapshot(insufficient=("satisfaction",))

    template = build_template_brief(snapshot, build_brief_facts(snapshot))

    assert "satisfaction" in template.summary
    assert "limited" in template.summary.lower() or "not enough" in template.summary.lower()


def test_the_template_direction_follows_that_components_stored_delta() -> None:
    snapshot = stored_snapshot()
    previous = stored_snapshot(
        as_of=AS_OF - timedelta(days=30), snapshot_id=10, overall_score="90.00"
    )
    # Complaint frequency fell from 80.00 to 60.00, which is this driver's own move.
    previous.frequency_score = Decimal("80.00")
    facts = build_brief_facts(snapshot, previous, None)

    template = build_template_brief(snapshot, facts)

    assert template.drivers[0].component == "frequency"
    assert template.drivers[0].direction == "declining"
    assert "declining" in template.drivers[0].statement
