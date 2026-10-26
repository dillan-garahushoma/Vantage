"""Contract tests for public unit-listing schema migration."""
import importlib.util
from pathlib import Path


class Recorder:
    def __init__(self):
        self.calls = []
        self.created_tables = []
        self.dropped_tables = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if name == "create_table":
                self.created_tables.append(args[0])
            if name == "drop_table":
                self.dropped_tables.append(args[0])
        return record


def migration():
    path = Path(__file__).resolve().parents[1] / "alembic/versions/c7e2a9b4d6f1_add_public_unit_listings.py"
    spec = importlib.util.spec_from_file_location("public_unit_listings", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_adds_private_by_default_listing_fields_and_photo_table(monkeypatch):
    module = migration()
    recorder = Recorder()
    monkeypatch.setattr(module, "op", recorder)
    module.upgrade()
    calls = repr(recorder.calls).lower()
    assert module.down_revision == "e8c3a1f9d5b7"
    for field in ("listing_title", "listing_description", "amenities", "is_public_listing", "availability_status", "public_listing_id", "ck_properties_availability_status"):
        assert field in calls
    assert recorder.created_tables == ["property_photos"]
    assert "ondelete='cascade'" in calls
    assert "ondelete='set null'" in calls


def test_downgrade_removes_only_new_listing_structures(monkeypatch):
    module = migration()
    recorder = Recorder()
    monkeypatch.setattr(module, "op", recorder)
    module.downgrade()
    calls = repr(recorder.calls).lower()
    assert "property_photos" in calls
    assert "availability_status" in calls
    assert "listing_description" in calls
    assert "listing_title" in calls
