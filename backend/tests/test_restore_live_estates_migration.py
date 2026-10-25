"""Live estates are restored with an exact flag rollback."""
import importlib.util
from pathlib import Path

from tests.test_restore_published_estates_migration import OperationRecorder


def migration():
    path = Path(__file__).resolve().parents[1] / 'alembic/versions/e8c3a1f9d5b7_restore_live_estates.py'
    spec = importlib.util.spec_from_file_location('restore_live_estates', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_restores_the_confirmed_estates_without_deleting_records(monkeypatch):
    module = migration()
    recorder = OperationRecorder()
    monkeypatch.setattr(module, 'op', recorder)
    module.upgrade()
    sql = ' '.join(recorder.statements)
    assert module.down_revision == 'a5c7e9f1b3d5'
    assert recorder.created_tables == [module._BACKUP_TABLE]
    assert 'is_demo = false' in sql and 'is_public = true' in sql
    assert 'show_living_score = true' in sql
    assert 'DELETE' not in sql.upper()
    for name in ('Eastbank Court', 'Lakeside Gardens', 'Quarry View Flats', 'Silverleaf Reserve', 'Willowbrook Mews'):
        assert name in sql


def test_downgrade_restores_the_saved_flags(monkeypatch):
    module = migration()
    recorder = OperationRecorder()
    monkeypatch.setattr(module, 'op', recorder)
    module.downgrade()
    sql = ' '.join(recorder.statements)
    assert 'is_demo = prior.is_demo' in sql
    assert 'is_public = prior.is_public' in sql
    assert 'show_living_score = prior.show_living_score' in sql
    assert recorder.dropped_tables == [module._BACKUP_TABLE]
