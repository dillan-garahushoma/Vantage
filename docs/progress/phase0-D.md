# Phase 0 — Batch D completion

**Result:** Offline Alembic SQL generation for the full chain passes.

## Verification

Run from the repository root with the backend virtual-environment interpreter and the backend as the working directory:

```powershell
Set-Location backend
& .\venv\Scripts\python.exe -m alembic upgrade head --sql
```

Initial attempt (exit code 1) failed in the D migration:

```text
AttributeError: 'MigrationContext' object has no attribute 'is_offline_mode'
EXIT_CODE=1
```

After the correction below, the same command passed (exit code 0). Alembic reported `Context impl PostgresqlImpl`, `Generating static SQL`, and generated SQL through each upgrade:

```text
-- Running upgrade  -> 5c5c0e0ef686
-- Running upgrade 5c5c0e0ef686 -> 103dd39ca30e
-- Running upgrade 103dd39ca30e -> a1d7e4f2b9c8
-- Running upgrade a1d7e4f2b9c8 -> b2e8f5c3d0a1
-- Running upgrade b2e8f5c3d0a1 -> c3f9a6d4e1b2
-- Running upgrade c3f9a6d4e1b2 -> d4a7e1c9b3f2
COMMIT;
EXIT_CODE=0
```

## Change made

In `backend/alembic/versions/d4a7e1c9b3f2_hardening_integrity_constraints.py`, changed the online-only pre-migration-check guard to use `op.get_context().as_sql`. `MigrationContext` has no `is_offline_mode()` method; the SQL-generation flag correctly prevents data queries during offline generation. No other application code was changed.

## Remaining concerns

- Live PostgreSQL application and the migration's data checks were not run. Offline generation does not establish that deployed data passes those checks or confirm the legacy constraint name against `pg_constraint`.
- Existing `ON DELETE CASCADE` behavior that can remove operational history remains unchanged and is a follow-up, as specified in the hardening instructions.
