"""The demo-estate classification correction is exercised without a live database."""
from __future__ import annotations

import importlib.util
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "e2f4c8b1a9d3_mark_seeded_demo_estates_private.py"
)


class OperationRecorder:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def create_table(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        return None

    def drop_table(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        return None

    def execute(self, statement: str) -> None:
        self.statements.append(statement)


def load_migration():
    spec = importlib.util.spec_from_file_location("seed_estate_flags_migration", MIGRATION_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_known_seed_estates_are_marked_demo_and_removed_from_public_surfaces(monkeypatch) -> None:
    migration = load_migration()
    recorder = OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)

    migration.upgrade()

    sql = " ".join(recorder.statements)
    for name in migration._NAMES:
        assert name in sql
    assert "is_demo = true" in sql
    assert "is_public = false" in sql
    assert "show_living_score = false" in sql
    assert "migration_e2f4c8b1a9d3_seed_estate_flags" in sql
