"""Current contracts must exist without re-enabling unsafe legacy routes."""
from app.main import app


def test_current_property_market_contracts_registered_and_legacy_absent():
    paths = app.openapi()['paths']
    for suffix, method in (
        ('/authorities', 'post'), ('/requests', 'post'),
        ('/requests/{request_id}/decision', 'post'), ('/listings', 'post'),
        ('/listings/{listing_id}/price', 'patch'),
        ('/listings/{listing_id}/price-history', 'get'),
        ('/listings/{listing_id}/complete', 'post'), ('/sales', 'get'),
    ):
        assert method in paths['/api/v1/property-market' + suffix]
    assert '/api/v1/listings' not in paths
    assert '/api/v1/sales' not in paths
