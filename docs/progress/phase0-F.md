# Phase 0 — Batch F: CI, Compose, dependencies, docs

**Date:** 2026-10-09
**Result:** Batch F is complete. No commits were created. The pre-existing dirty and untracked work was preserved.

## Findings and changes

- CI previously performed only a syntax-focused flake8 check. It now installs from `backend/requirements.txt` constrained by `backend/constraints.txt`, runs `pytest backend/tests -q`, compiles `backend/app`, generates offline Alembic SQL, and retains the existing flake8 gate. CI supplies `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, and `PYTHONPATH`; it intentionally does not set `TEST_DATABASE_URL`, so DB-backed tests skip safely.
- Compose previously exposed a frontend on port 4173 from the nonexistent `../FrontEnd` path. The frontend is now behind the `frontend` profile, uses `../frontend`, maps port 5173, and binds Vite to `0.0.0.0`. The API has explicit CORS origins for localhost and 127.0.0.1 on port 5173. No frontend was created.
- `backend/constraints.txt` was generated from the known-good backend venv's `pip freeze`. `httpx2` was removed from `backend/requirements.txt` after the entire suite passed with the package uninstalled.
- `test_api_error_contract.py` now uses `httpx.AsyncClient` and `ASGITransport`.
- Added ADR-002 for `EstateAccess`, the dual-role rule, and membership uniqueness; ADR-003 records legacy-route isolation and provider rating as a single-writer flow. ADR-001 now reflects the implemented tenant boundary and migration state.
- The requested roadmap and implementation-status names were absent from the real tree. Created `docs/EXECUTION_ROADMAP.md` and `docs/VALORA_IMPLEMENTATION_STATUS.md` as the current documents, and pointed the existing `PROJECT_STATUS.md` and `VALORA_Development_Roadmap.md` at them. Added the Hardening pass H checklist and anonymity limitation to `tasks/todo.md`.
- Updated `phase0-partial.md` so its batch status agrees with the D, E, and F reports.

## Files changed for Batch F

- `.github/workflows/ci.yml`
- `backend/constraints.txt` (new)
- `backend/docker-compose.yml`
- `backend/requirements.txt`
- `backend/tests/test_api_error_contract.py`
- `docs/ADR-001-Estate-Tenancy.md`
- `docs/ADR-002-estate-authorization.md` (new)
- `docs/ADR-003-legacy-isolation-and-provider-ratings.md` (new)
- `docs/EXECUTION_ROADMAP.md` (new)
- `docs/VALORA_IMPLEMENTATION_STATUS.md` (new)
- `docs/PROJECT_STATUS.md`
- `docs/VALORA_Development_Roadmap.md`
- `docs/progress/phase0-partial.md`
- `docs/progress/phase0-F.md` (this report)
- `tasks/todo.md`

## Commands and results

| Command | Result |
|---|---|
| `& .\backend\venv\Scripts\python.exe -m pip show httpx2` | Found `httpx2 2.13.1`; details below. |
| `& .\backend\venv\Scripts\python.exe -m pip freeze \| Set-Content -Path .\backend\constraints.txt -Encoding utf8` | Passed; constraints refreshed after removal of `httpx2`. |
| `$env:PYTHONPATH='backend'; & .\backend\venv\Scripts\python.exe -m pytest backend/tests -q` (with `httpx2` uninstalled) | **47 passed, 1 skipped, 3 warnings**. Exit 0. |
| `$env:PYTHONPATH='backend'; & .\backend\venv\Scripts\python.exe -m pytest backend/tests/test_api_error_contract.py -q` (without `httpx2`) | **2 passed, 2 warnings**. Exit 0. |
| `& .\backend\venv\Scripts\python.exe -m compileall -q backend/app` | Passed. Exit 0. |
| `& .\backend\venv\Scripts\python.exe -m flake8 backend/app --count --select=E9,F63,F7,F82 --show-source --statistics` | Passed; **0 findings**. |
| From `backend`: `& .\venv\Scripts\python.exe -m alembic upgrade head --sql` | Passed. Exit 0; generated SQL through revision `d4a7e1c9b3f2`. No database connection was made. |
| `& .\backend\venv\Scripts\python.exe -m pip check` | Passed; no broken requirements. |
| `& .\backend\venv\Scripts\python.exe -m pip install --dry-run -r .\backend\requirements.txt -c .\backend\constraints.txt` | Passed; installed versions satisfy the declared requirements and constraints. |
| `git diff --check -- .github/workflows/ci.yml backend/docker-compose.yml backend/requirements.txt backend/tests/test_api_error_contract.py docs/ADR-001-Estate-Tenancy.md docs/PROJECT_STATUS.md docs/VALORA_Development_Roadmap.md docs/progress/phase0-partial.md tasks/todo.md` | Passed. Exit 0. |
| Trailing-whitespace scan of new constraints, ADRs, roadmap/status docs, and this report | Passed after removing two accidental trailing spaces from the new status file. |
| YAML parse and structure assertions for `.github/workflows/ci.yml` and `backend/docker-compose.yml` | Passed; required workflow steps, profile, port, mount, and CORS JSON were verified. |
| `git diff --check` (whole shared worktree) | Exit 2 because the already-modified, out-of-scope `docs/VALORA_PRD.md:6` has trailing whitespace. The Batch F tracked-file check above passes; that file was not changed for Batch F. |

The initial YAML validation command failed because its test incorrectly assumed the CORS entry was the final item in the API environment list; the entry is present but precedes the database and secret entries. The corrected assertion checks for it by key and passed. No Compose file change was needed for that validation-script mistake.

## `httpx2` provenance check and decision

Before removal, local metadata reported version `2.13.1`, summary “The next generation HTTP client,” author email `Tom Christie <tom@tomchristie.com>`, BSD-3-Clause licensing, and project URL `https://github.com/pydantic/httpx2`. The public [PyPI project page](https://pypi.org/project/httpx2/2.13.1/) links to the `pydantic/httpx2` source repository; the [repository page](https://github.com/pydantic/httpx2) states that Pydantic picked up stewardship under the HTTPX2 name and credits the original HTTPX project and `@lovelydinosaur`. This metadata/source-link review found no suspicious provenance signal; it is not a complete security or artifact-signature audit.

The prior direct dependency existed because Starlette's synchronous `TestClient` uses the newer transport package and emits a deprecation warning when only `httpx` is present. After converting the required error-contract tests to `AsyncClient`/`ASGITransport`, the **full suite passed with `httpx2` uninstalled**. Therefore the direct `httpx2` requirement was removed. Other existing tests still use Starlette `TestClient`; they passed with `httpx` and emit a warning recommending `httpx2`, but do not require it to execute.

## Not run / limitations

- Integration tests requiring `TEST_DATABASE_URL` were skipped. No Docker-backed test database was provisioned, and no migration was applied to a live/clean PostgreSQL database. To run the DB tests, provision a disposable PostgreSQL database with a database name containing `test`, export a valid `TEST_DATABASE_URL` (for example `postgresql+asyncpg://<user>:<password>@<host>:5432/valora_test`), then run `pytest backend/tests -q`. The harness refuses names without `test` and truncates tables in the designated database.
- The GitHub Actions workflow was updated but not dispatched in GitHub; its component commands were run locally as shown above.
- No frontend was created, started, or browser-tested. Compose runtime startup was not run.
- Phase 1 and the other later product tasks were not started.

## Deviations and open questions

- `EXECUTION_ROADMAP.md` and `VALORA_IMPLEMENTATION_STATUS.md` did not exist in the inspected worktree. They were created under `docs/` and the existing historical status/roadmap documents now link to them.
- The broad `git diff --check` is not clean solely because of the pre-existing `docs/VALORA_PRD.md:6` trailing whitespace. It was left untouched to preserve unrelated work.
- No blocking questions remain. The live PostgreSQL checks above remain acceptance follow-ups.
