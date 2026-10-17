"""API contracts for advisory AI triage suggestions (BATCH AI-3).

The response shows what was suggested, who produced it and what an HOA admin
decided. It deliberately has no field for the prompt, the provider's raw output
or the complaint text: none of that is stored.

The label fields are typed with the vocabulary aliases, so the OpenAPI contract
publishes the allowed values and a client never has to retype them.
"""
from datetime import datetime

from pydantic import BaseModel, Field

from app.community.domain.triage_vocabulary import Category, Decision, Priority, Trade


class TriageDecisionRequest(BaseModel):
    """An HOA admin's decision on one suggestion.

    ``accepted`` copies the suggestion; ``overridden`` supplies at least one
    corrected label; ``dismissed`` supplies none. Which combination is legal is
    decided by the service, because only it knows the suggestion being decided.
    """

    decision: Decision
    category: Category | None = None
    priority: Priority | None = None
    trade: Trade | None = None


class TriageSuggestionResponse(BaseModel):
    """One stored suggestion and its (write-once) decision."""

    suggestion_id: int = Field(..., serialization_alias="id")
    complaint_id: int
    estate_id: int
    suggested_category: Category
    suggested_priority: Priority
    suggested_trade: Trade | None
    provider: str
    model: str
    prompt_version: str
    decision: str | None
    decided_by: int | None
    decided_at: datetime | None
    decided_category: Category | None
    decided_priority: Priority | None
    decided_trade: Trade | None
    created_at: datetime | None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "serialize_by_alias": True,
    }
