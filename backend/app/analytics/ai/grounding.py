"""Grounding: the brief may only say what FACTS already say (BATCH AI-4).

Schema validation proves the *shape* of a provider's answer; it cannot prove the
answer is true. This module proves the other half:

* every number in the brief's text must equal a number in FACTS, compared by
  absolute value and allowed to differ only by rounding to 0, 1 or 2 decimal
  places (half up) - so a model may write "83.3" for 83.32, or "1.13" for a delta
  of -1.13, and nothing else;
* every component named must be one of the engine's five keys;
* anything else is a violation, and a violation means the answer is discarded and
  the deterministic template is used instead.

The check is deliberately strict about units: a fact of 30 must not be written as
0.30. It is not a spell-check for prose - it cannot judge whether a sentence is
misleading in other ways - so the brief remains advisory text beside the numbers,
never a source of new ones.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Final

from app.analytics.ai.brief_facts import COMPONENT_KEYS, BriefFacts

UNGROUNDED_NUMBER: Final[str] = "ungrounded_number"
UNKNOWN_COMPONENT: Final[str] = "unknown_component"

_QUANTIZERS: Final[tuple[Decimal, ...]] = (
    Decimal("1"),
    Decimal("0.1"),
    Decimal("0.01"),
)

# A sentence-ending period is not part of a number. Cleaned first so that
# "83.32." is read as 83.32 rather than skipped entirely.
_SENTENCE_PERIOD: Final = re.compile(r"\.(?=\s|$)")

# A number token: not glued to a word or to another dotted number.
_NUMBER: Final = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])")


class GroundingViolation(Exception):
    """The brief said something FACTS do not support."""

    def __init__(self, code: str) -> None:
        self.code: str = code
        super().__init__(f"Ungrounded brief output ({code}).")


def allowed_values(facts: BriefFacts) -> frozenset[Decimal]:
    """Every number the brief is allowed to print, at each permitted rounding."""
    return frozenset(
        rounded
        for value in fact_numbers(facts)
        for rounded in _permitted_roundings(value)
    )


def fact_numbers(facts: BriefFacts) -> frozenset[Decimal]:
    """Every number in FACTS, whatever its nesting."""
    return frozenset(_walk(facts.model_dump(mode="python")))


def numbers_in(text: str) -> list[Decimal]:
    """Every number written in a piece of text, in order."""
    found: list[Decimal] = []
    for match in _NUMBER.finditer(_SENTENCE_PERIOD.sub(" ", text)):
        try:
            found.append(Decimal(match.group(0)))
        except (InvalidOperation, ValueError):  # pragma: no cover - regex-guarded
            continue
    return found


def validate_grounding(output: Any, facts: BriefFacts) -> None:
    """Raise :class:`GroundingViolation` unless the output is fully grounded.

    ``output`` is a :class:`~app.analytics.ai.brief_output.BriefOutput`; attribute
    access is used so the check does not depend on pydantic having run.
    """
    for component in _named_components(output):
        if component not in COMPONENT_KEYS:
            raise GroundingViolation(UNKNOWN_COMPONENT)

    permitted = allowed_values(facts)
    for text in _texts(output):
        for number in numbers_in(text):
            if abs(number) not in permitted:
                raise GroundingViolation(UNGROUNDED_NUMBER)


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #
def _permitted_roundings(value: Decimal) -> set[Decimal]:
    magnitude = abs(value)
    return {magnitude} | {
        magnitude.quantize(quantizer, rounding=ROUND_HALF_UP)
        for quantizer in _QUANTIZERS
    }


def _walk(value: Any) -> list[Decimal]:
    """Collect the numbers in a dumped model, ignoring text and timestamps."""
    if isinstance(value, bool):
        return []
    if isinstance(value, Decimal):
        return [value]
    if isinstance(value, int):
        return [Decimal(value)]
    if isinstance(value, float):
        return [Decimal(str(value))]
    if isinstance(value, dict):
        return [number for item in value.values() for number in _walk(item)]
    if isinstance(value, (list, tuple)):
        return [number for item in value for number in _walk(item)]
    return []


def _named_components(output: Any) -> list[Any]:
    named: list[Any] = []
    for driver in getattr(output, "drivers", None) or []:
        named.append(getattr(driver, "component", None))
    for action in getattr(output, "actions", None) or []:
        named.append(getattr(action, "component", None))
    return named


def _texts(output: Any) -> list[str]:
    """Every piece of text a reader will see."""
    texts: list[str] = []
    for attribute in ("headline", "summary"):
        value = getattr(output, attribute, None)
        if isinstance(value, str):
            texts.append(value)
    for driver in getattr(output, "drivers", None) or []:
        statement = getattr(driver, "statement", None)
        if isinstance(statement, str):
            texts.append(statement)
    for action in getattr(output, "actions", None) or []:
        text = getattr(action, "action", None)
        if isinstance(text, str):
            texts.append(text)
    return texts
