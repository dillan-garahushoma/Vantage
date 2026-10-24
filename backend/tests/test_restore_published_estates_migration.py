"""The owner-confirmed published estates are restored without touching other rows."""
from __future__ import annotations

import importlib.util
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "f3a6b2c9d1e4_restore_owner_confirmed_estates.py"
)


class OperationRecorder:
    def __init__(self) -> None:
        self.statements: list[str] = []
        self.created_tables: list[str] = []
        self.dropped_tables: list[str] = []

    def create_table(self, name: str, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        self.created_tables.append(name)

    def drop_table(self, name: str, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        self.dropped_tables.append(name)

    def execute(self, statement: str) -> None:
        self.statements.append(statement)


def load_migration():
    spec = importlib.util.spec_from_file_location(
        "restore_owner_confirmed_estates_migration", MIGRATION_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_publishes_only_the_five_owner_confirmed_estates(monkeypatch) -> None:
    migration = load_migration()
    recorder = OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)

    migration.upgrade()

    sql = " ".join(recorder.statements)
    for name in migration._NAMES:
        assert name in sql
    assert "estate.name IN" in sql
    assert "is_demo = false" in sql
    assert "is_public = true" in sql
    assert "migration_e2f4c8b1a9d3_seed_estate_flags" in sql
    assert f"AND estate.name IN ({migration._NAME_LIST})" in sql
    assert "name = 'musgrave'" in sql
    assert "suburb = 'pinetown'" in sql
    assert "city = 'durban'" in sql
    assert "province = 'KwaZulu-Natal'" in sql
    assert "UPDATE estates SET is_public = false" in sql
    assert "DELETE FROM estates" not in sql
    assert recorder.created_tables == [migration._BACKUP_TABLE]


def test_downgrade_restores_pre_migration_flags(monkeypatch) -> None:
    migration = load_migration()
    recorder = OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)

    migration.downgrade()

    sql = " ".join(recorder.statements)
    assert "SET is_demo = prior.is_demo" in sql
    assert "is_public = prior.is_public" in sql
    assert "show_living_score = prior.show_living_score" in sql
    assert recorder.dropped_tables == [migration._BACKUP_TABLE]
