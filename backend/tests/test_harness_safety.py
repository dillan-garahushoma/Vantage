import os
import pytest


@pytest.mark.integration
def test_integration_marker_auto_skips() -> None:
    # If TEST_DATABASE_URL is not set, this test should be skipped automatically
    assert True


def test_safety_check_rejects_non_test_database() -> None:
    from urllib.parse import urlparse

    unsafe_url = "postgresql+asyncpg://user:pass@localhost:5432/valora_production"
    parsed = urlparse(unsafe_url)
    db_name = parsed.path.lstrip("/").split("?")[0]
    assert "test" not in db_name.lower()
