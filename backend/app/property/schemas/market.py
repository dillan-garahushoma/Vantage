"""Current estate market DTOs; amounts are ZAR, rental asking prices per month."""
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Id = Annotated[int, Field(gt=0, le=2147483647, strict=True)]
Amount = Annotated[Decimal, Field(gt=0, le=9999999999, max_digits=12, decimal_places=2)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Purpose = Literal['sale', 'rent']


class DTO(BaseModel):
    model_config = ConfigDict(extra='forbid', from_attributes=True, allow_inf_nan=False)

    @field_validator('*', mode='before')
    @classmethod
    def no_nul(cls, value):
        if isinstance(value, str) and '\x00' in value:
            raise ValueError('NUL characters are not supported.')
        return value


class AuthorityCreate(DTO):
    property_id: Id
    representative_id: Id
    verification_reference: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=240)]


class Reason(DTO):
    reason: Text


class AuthorityResponse(DTO):
    authority_id: int
    estate_id: int
    property_id: int
    representative_id: int
    verified_by: int
    verification_reference: str
    created_at: datetime
    revoked_at: datetime | None
    revoked_by: int | None


class RequestCreate(DTO):
    property_id: Id
    purpose: Purpose
    requested_price: Amount
    notes: Text | None = None


class RequestDecision(DTO):
    decision: Literal['approved', 'rejected']
    reason: Text
    agent_id: Id | None = None


class RequestResponse(DTO):
    request_id: int
    estate_id: int
    property_id: int
    authority_id: int
    requester_id: int
    purpose: Purpose
    requested_price: Decimal
    notes: str | None
    status: str
    agent_id: int | None
    decision_reason: str | None
    decided_by: int | None
    created_at: datetime
    decided_at: datetime | None


class ListingCreate(DTO):
    request_id: Id
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=160)]
    description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=4000)]
    asking_price: Amount


class ListingResponse(DTO):
    listing_id: int
    estate_id: int
    property_id: int
    purpose: Purpose
    title: str
    description: str
    asking_price: Decimal
    currency: Literal['ZAR'] = 'ZAR'
    status: str
    version: int
    created_at: datetime
    published_at: datetime | None


class ListingAction(DTO):
    action: Literal['publish', 'withdraw']
    expected_version: Id
    reason: Text


class ListingContent(DTO):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=160)]
    description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=4000)]
    expected_version: Id
    reason: Text


class PriceChange(DTO):
    asking_price: Amount
    expected_version: Id
    reason: Text


class PriceResponse(DTO):
    price_id: int
    estate_id: int
    listing_id: int
    old_price: Decimal | None
    new_price: Decimal
    changed_by: int
    reason: str
    listing_version: int
    created_at: datetime


class CompletionCreate(DTO):
    actual_amount: Amount
    effective_date: date
    expected_version: Id
    reference: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=240)]


class TransactionResponse(DTO):
    transaction_id: int
    estate_id: int
    property_id: int
    listing_id: int
    purpose: Purpose
    actual_amount: Decimal
    asking_price_at_completion: Decimal
    effective_date: date
    recorded_by: int
    reference: str
    created_at: datetime


class EventResponse(DTO):
    event_id: int
    estate_id: int
    entity_type: str
    entity_id: int
    action: str
    actor_id: int
    details: dict
    created_at: datetime
