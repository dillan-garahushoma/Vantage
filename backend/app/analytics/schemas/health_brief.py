"""API contracts for the estate health brief (BATCH AI-4).

The response says whether the text came from the AI layer or from the
deterministic template, and - when it is a template - why no AI brief is present.
It carries the FACTS the brief was built from, so a reader can check every number
in the sentences against the numbers underneath them.

There is no field for a prompt, a system message or a raw provider response:
none of that is stored, so none of it can be returned.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.ai.brief_facts import BriefFacts
from app.analytics.ai.brief_output import BriefOutput
from app.analytics.domain.insight_vocabulary import FEEDBACK_COMMENT_MAX_LENGTH

#: Where the brief's text came from.
BriefSource = Literal["ai", "template"]

#: Why no AI brief is present. Closed on purpose: a client may switch on it.
#: ``insufficient_data`` is not an AI failure - it means the score itself is not
#: yet measurable, so there was nothing worth sending to a provider.
#: ``truncated`` means the provider did answer but ran out of output tokens,
#: which is an operator setting (AI_MAX_OUTPUT_TOKENS / AI_THINKING_LEVEL),
#: not a bad answer and not a bad key. ``rate_limited`` means the provider's quota
#: or rate limit refused the call: the key works, the allowance does not.
BriefUnavailableReason = Literal[
    "disabled",
    "policy",
    "budget",
    "timeout",
    "network",
    "provider_error",
    "rate_limited",
    "invalid_output",
    "truncated",
    "ungrounded_output",
    "insufficient_data",
]

#: Whether the estate the brief describes is real or a seeded demonstration.
DataOrigin = Literal["demo", "live"]

_DTO_CONFIG = ConfigDict(
    from_attributes=True, populate_by_name=True, serialize_by_alias=True
)


class HealthBriefFeedbackRequest(BaseModel):
    """A member's verdict on one stored brief. No extra fields: nothing to smuggle."""

    model_config = ConfigDict(extra="forbid")

    helpful: bool
    #: Stored locally and never sent to a provider. Bounded by the DTO and again
    #: by a database check, because the DTO is not the only way in.
    comment: str | None = Field(default=None, max_length=FEEDBACK_COMMENT_MAX_LENGTH)


class HealthBriefFeedbackResponse(BaseModel):
    """One stored verdict."""

    feedback_id: int = Field(..., serialization_alias="id")
    insight_id: int
    estate_id: int
    #: NULL after the member's account is deleted; the verdict survives.
    user_id: int | None
    helpful: bool
    comment: str | None
    created_at: datetime | None

    model_config = _DTO_CONFIG


class HealthBriefResponse(BaseModel):
    """The estate's brief, with the numbers it was allowed to use."""

    source: BriefSource
    #: NULL for a template: a template is rebuilt from the snapshot on demand and
    #: is never stored, so it has no row to point at.
    insight_id: int | None
    ai_unavailable_reason: BriefUnavailableReason | None
    data_origin: DataOrigin
    snapshot_id: int
    as_of: datetime
    #: When the stored AI brief was written. NULL for a template, which has no
    #: generation event - it exists only for the length of this response.
    generated_at: datetime | None
    #: The numbers the brief was built from, stored beside an AI brief so the
    #: sentences can be checked against them later.
    facts: BriefFacts
    output: BriefOutput
    provider: str | None
    model: str | None
    prompt_version: str | None

    model_config = _DTO_CONFIG
