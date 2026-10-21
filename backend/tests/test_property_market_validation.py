"""Reject ambiguous prices, forged ownership, oversized IDs and invalid text."""
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.property.schemas.market import AuthorityCreate, RequestCreate, PriceChange


@pytest.mark.parametrize('price', ['0', '-1', 'NaN', 'Infinity', '1350000.001', '10000000000'])
def test_request_requires_finite_positive_cent_precision_amount(price):
    with pytest.raises(ValidationError):
        RequestCreate(property_id=1, purpose='sale', requested_price=price)


@pytest.mark.parametrize('changes', [
    {'owner_id': 8}, {'requester_id': 8}, {'status': 'approved'}, {'agent_id': 9},
    {'property_id': 2147483648}, {'property_id': True}, {'notes': '\x00'},
])
def test_request_cannot_forge_identity_or_lifecycle(changes):
    with pytest.raises(ValidationError):
        RequestCreate.model_validate({'property_id': 1, 'purpose': 'rent', 'requested_price': '11500'} | changes)


def test_prices_are_decimal_and_revision_requires_reason_and_version():
    assert RequestCreate(property_id=1, purpose='rent', requested_price='11500.50').requested_price == Decimal('11500.50')
    for changes in ({'expected_version': 0}, {'reason': '  '}, {'changed_by': 9}):
        with pytest.raises(ValidationError):
            PriceChange.model_validate({'asking_price': '12000', 'expected_version': 1, 'reason': 'Owner instruction'} | changes)
    with pytest.raises(ValidationError):
        AuthorityCreate(property_id=1, representative_id=2, verification_reference='  ')
