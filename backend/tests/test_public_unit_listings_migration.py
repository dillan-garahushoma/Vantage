"""Contract tests for public unit-listing schema migration."""
import importlib.util
from pathlib import Path

from tests.test_restore_published_estates_migration import OperationRecorder


def migration():
    path = Path(__file__).resolve().parents[1] / "alembic/versions/c7e2a9b4d6f1_add_public_unit_listings.py"
    spec = importlib.util.spec_from_file_location("public_unit_listings", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_adds_private_by_default_listing_fields_and_photo_table(monkeypatch):
    module = migration()
    recorder = OperationRecorder()
    monkeypatch.setattr(module, "op", recorder)
    module.upgrade()
    sql = " ".join(recorder.statements).lower()
    assert module.down_revision == "e8c3a1f9d5b7"
    assert "listing_title" in sql
    assert "listing_description" in sql
    assert "amenities" in sql
    assert "is_public_listing" in sql
    assert "'false'" in sql or "false" in sql
    assert "availability_status" in sql
    assert recorder.created_tables == ["property_photos"]
    assert "on delete cascade" in sql
    assert "on delete set null" in sql


def test_downgrade_removes_only_new_listing_structures(monkeypatch):
    module = migration()
    recorder = OperationRecorder()
    monkeypatch.setattr(module, "op", recorder)
    module.downgrade()
    sql = " ".join(recorder.statements).lower()
    assert "property_photos" in sql
    assert "availability_status" in sql
    assert "listing_description" in sql
    assert "listing_title" in sql
