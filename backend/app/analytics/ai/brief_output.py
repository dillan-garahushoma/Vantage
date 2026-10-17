"""The brief's prompt, provider schema and output shape (BATCH AI-4).

The model is a writer, not an analyst. It is handed FACTS - numbers, enums and
dates - and asked to put them into English. Everything a language model could do
with the numbers (decide them, extrapolate them, advise beyond the stored text)
is out of scope by instruction, and anything it invents is caught afterwards by
:mod:`app.analytics.ai.grounding` and rejected.

There is no resident text in this prompt at all, so there is nothing to escape
and nothing to inject: the whole input is a projection of a stored score row.
"""
from __future__ import annotations

import json
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.ai.brief_facts import BriefFacts, ComponentKey

#: Bumped whenever the prompt, the schema or the writing rules change.
PROMPT_VERSION: Final[str] = "brief-v1"

DIRECTIONS: Final[tuple[str, ...]] = ("improving", "declining", "stable")

HEADLINE_MAX: Final[int] = 120
SUMMARY_MAX: Final[int] = 600
STATEMENT_MAX: Final[int] = 200
ACTION_MAX: Final[int] = 200
MAX_DRIVERS: Final[int] = 3
MAX_ACTIONS: Final[int] = 3

SYSTEM_PROMPT: Final[str] = (
    "You write a short estate health brief for a South African residential estate "
    "management system. You explain the FACTS given to you; you never calculate "
    "anything and you never re-derive a number.\n"
    "Rules:\n"
    "- Use only numbers that appear in FACTS, written as digits, copied exactly as "
    "they appear. Never introduce another number, an estimate, a percentage, a "
    "target, a currency amount or a score of your own.\n"
    "- FACTS values are decimal strings; copy the digits, do not round or reformat "
    "them, and do not write a number in a different unit.\n"
    "- Do not give a valuation, a price, a prediction, a forecast, or safety, legal, "
    "insurance or financial advice.\n"
    "- Where a component's status is insufficient_data, say plainly that the data "
    "for that component is still limited.\n"
    "- Do not mention being an AI, a model, a prompt or an engine version.\n"
    "- Never include a person's name, an email address, a phone number, a unit "
    "number, an estate name or any text written by a resident. You have not been "
    "given any such text.\n"
    "- Write for an estate trustee: plain, specific, neutral, no blame.\n"
    "- You have no tools and you cannot change any data.\n"
    "Reply with JSON only, matching the provided schema, and nothing else."
)


class BriefDriver(BaseModel):
    """What is holding the score back, and which way it is moving."""

    model_config = ConfigDict(extra="forbid")

    component: ComponentKey
    direction: Literal["improving", "declining", "stable"]
    statement: str = Field(..., min_length=1, max_length=STATEMENT_MAX)


class BriefAction(BaseModel):
    """One thing the estate could do, tied to the component it belongs to."""

    model_config = ConfigDict(extra="forbid")

    component: ComponentKey
    action: str = Field(..., min_length=1, max_length=ACTION_MAX)


class BriefOutput(BaseModel):
    """The brief itself. Provider output is validated against exactly this."""

    model_config = ConfigDict(extra="forbid")

    headline: str = Field(..., min_length=1, max_length=HEADLINE_MAX)
    summary: str = Field(..., min_length=1, max_length=SUMMARY_MAX)
    drivers: list[BriefDriver] = Field(default_factory=list, max_length=MAX_DRIVERS)
    actions: list[BriefAction] = Field(default_factory=list, max_length=MAX_ACTIONS)


def build_user_prompt(facts: BriefFacts) -> str:
    """Render the FACTS block.

    ``None`` is dropped rather than sent as ``null``: a missing comparison is not
    a value, and an empty field could be read as a zero.
    """
    payload = facts.model_dump(mode="json", exclude_none=True)
    return "FACTS:\n" + json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)


def brief_output_schema() -> dict[str, Any]:
    """The JSON schema asked of the provider.

    A fresh object every call, built from the same vocabulary the model and the
    validator use, so a provider cannot return a component the system refuses.
    """
    driver = {
        "type": "object",
        "properties": {
            "component": {"type": "string", "enum": list(ComponentKey.__args__)},
            "direction": {"type": "string", "enum": list(DIRECTIONS)},
            "statement": {"type": "string"},
        },
        "required": ["component", "direction", "statement"],
        "additionalProperties": False,
    }
    action = {
        "type": "object",
        "properties": {
            "component": {"type": "string", "enum": list(ComponentKey.__args__)},
            "action": {"type": "string"},
        },
        "required": ["component", "action"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "headline": {"type": "string"},
            "summary": {"type": "string"},
            # The same list limits BriefOutput enforces. Without them the model
            # answered with five drivers against a three-driver contract, and a
            # usable brief was discarded as invalid output.
            "drivers": {"type": "array", "items": driver, "maxItems": MAX_DRIVERS},
            "actions": {"type": "array", "items": action, "maxItems": MAX_ACTIONS},
        },
        "required": ["headline", "summary", "drivers", "actions"],
        "additionalProperties": False,
    }
