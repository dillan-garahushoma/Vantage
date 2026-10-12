# BATCH 7C — Living Score endpoints, CLI recalculation, documentation

**Date:** 2026-10-11 · **Scope:** one schema module, one thin router, one CLI
subcommand, two documentation artifacts, one OpenAPI regeneration. **No migration**
(7B's `c4d8f1a7b9e3` is unchanged and is still head). Legacy
`LegacyPropertyScore*` untouched, as required.

## Prerequisites (verified before writing code)

- **7B** is in the tree: `living_score_snapshots` (head `c4d8f1a7b9e3`),
  `LivingScoreSnapshotRepository`, `LivingScoreInputsRepository`,
  `LivingScoreService.calculate_and_snapshot/latest/history`.
- **7A** engine present at version `1.0.0`.
- A **running PostgreSQL** was found on this workstation (see "Notable finding"),
  so this batch's integration tests were **run**, not skipped.

## Done

| File | Contents |
|---|---|
| `backend/app/analytics/schemas/living_score_snapshot.py` | `LivingScoreSnapshotResponse`, `LivingScoreComponentResponse`, `LivingScoreHistoryRow`, `LivingScoreHistoryResponse`. Every field is a projection of the stored row; nothing is recomputed on read. |
| `backend/app/analytics/api/living_score.py` | The three thin routes. Authorization lives in the service; the router does no maths. |
| `backend/app/analytics/api/router.py` | One line: includes the new router under `/analytics`. |
| `backend/app/analytics/services/estate_living_score_service.py` | Additive: `latest_view`, `recalculate_view`, `recalculate_estates`, `_is_demo`, plus the 7B `latest`/`history` reads. |
| `backend/app/property/repositories/estate_repository.py` | Additive: `scoring_statement` (pure, testable) + `list_ids_for_scoring`. Real estates only unless `include_demo`. |
| `backend/app/cli.py` | Additive: `recalc-living-scores [--estate-id N] [--include-demo]`. |
| `backend/tests/test_living_score_api.py` | **45 tests** (15 integration), written first — first run was `29 failed, 2 passed, 14 skipped`. |
| `docs/LIVING_SCORE_V1.md` | The formula, D1–D6, the insufficient-data rule, the endpoints, the CLI, and the version rule. |
| `docs/openapi.json` | Regenerated with the existing `python -m app.cli export-openapi`. |
| `tasks/todo.md` | Task 6 and Task 7 ticked, each with a verification line pointing at the commands below. |

### Endpoints

| Method | Path | Who | Result |
|---|---|---|---|
| `GET` | `/api/v1/analytics/living-score?estate_id=` | estate member | Latest stored snapshot; `404` (`RESOURCE_NOT_FOUND`) when never scored |
| `POST` | `/api/v1/analytics/living-score/recalculate?estate_id=` | global `hoa_admin` **and** member of that estate | `201` with the new snapshot |
| `GET` | `/api/v1/analytics/living-score/history?estate_id=&page=&page_size=` | estate member | Newest-first page; `page ≥ 1`, `1 ≤ page_size ≤ 100` (default 20) |

The estate is always a query parameter and is authorized against a persisted
membership inside the service. `is_demo` is read from the estate at response time, so a
snapshot never has to be rewritten to carry it. `calculated_by` stays internal.

### CLI

```
python -m app.cli recalc-living-scores [--estate-id N] [--include-demo]
```

One line per estate (`estate <id>: status=... score=... engine=...`), operational
metadata only. Real estates only by default. No queue and no scheduler in the
application: the daily cadence belongs to the Windows Task Scheduler job that calls
this command, which is what the doc says.

## Tests added and passing

| Command (from `backend/`) | Result |
|---|---|
| `pytest tests/test_living_score_engine.py -q` | **43 passed** |
| `pytest tests/test_living_score_snapshots.py -q` | **80 passed** |
| `pytest tests/test_living_score_api.py -q` | **45 passed** |
| `pytest tests -q` (no `TEST_DATABASE_URL`) | **501 passed, 44 skipped** |
| `pytest tests -q` (with `TEST_DATABASE_URL`) | **545 passed, 0 skipped** |
| `python -m compileall -q app` | clean |
| `flake8 app tests --count --select=E9,F63,F7,F82` | **0** |
| `git diff --check` | clean (only pre-existing CRLF notices on stderr) |
| `python -m alembic -c alembic.ini heads` | `c4d8f1a7b9e3 (head)` |
| `python -m alembic -c alembic.ini upgrade head --sql` | 480 lines, 21 `CREATE TABLE`, exit 0 |

Batch coverage: resident cannot recalculate (403, and nothing is written); an admin of
estate A cannot read or recalculate estate B (403 for a non-member, 404 for the wrong
estate's object); member read works; 404 when no snapshot exists; history pagination
bounds; history values unchanged after the underlying complaints/incidents/ratings
change (immutability); no response carries raw complaint text or personal data; error
envelope shape and `X-Request-ID`; the CLI skips demo estates by default and can be
targeted with `--estate-id`.

### Notable finding

Docker and a live PostgreSQL 15 (`valora_db`, and a `valora_test` database from an
earlier session) were **available** on this workstation, contrary to the "Docker/
PostgreSQL unavailable" note carried in earlier progress files. This batch therefore
ran its integration tests against a real database. A disposable
`valora_test_batch7c` database was created for the run; `valora_db` was never touched.
Note for future sessions: `tests/conftest.py` needs **both** `TEST_DATABASE_URL` **and**
`DATABASE_URL` pointed at the test database, because `alembic/env.py` takes its URL
from settings, not from the config override.

```bash
docker exec valora_db psql -U valora_user -d valora_db -c "CREATE DATABASE valora_test_batch7c;"
export DATABASE_URL="postgresql+asyncpg://valora_user:valora_password@localhost:5432/valora_test_batch7c"
export TEST_DATABASE_URL="$DATABASE_URL"
export SECRET_KEY="test-secret-not-for-production"
```

## Deviations and corrections

1. **A 7B test was updated, deliberately.** `test_no_api_module_reaches_the_calculation_service`
   asserted "the service is not wired to HTTP at all". 7C wires it to exactly one thin
   router, so the guard now asserts the new invariant: only `app/cli.py` and
   `app/analytics/api/living_score.py` may name `LivingScoreService`, and no other API
   module may reach the service module. The engine/repository ban on the routers is
   covered separately in `test_living_score_api.py`.
2. **Three bugs in my own new tests, found by running them** (all test-side, no
   production change): route inspection read `app.routes`, which on this FastAPI version
   keeps included routers wrapped, so it is now read from `app.openapi()`; the
   `drivers[0]` expectation said `resolution` when the seeded estate's real worst drag is
   `frequency` (10.00 lost points versus ~0.34), and the assertion is now the sorted-by-
   lost-points check plus the correct driver; the 401 envelope code is `UNAUTHENTICATED`,
   not `NOT_AUTHENTICATED`.
3. **`docs/openapi.json` diff is larger than 7C.** The committed file was stale relative
   to earlier batches (announcements, incidents, the AI ledger), so regenerating it
   exports those pending contract changes too: 1956 insertions, 410 deletions. Only the
   three `living-score` paths are this batch's. Regenerating was the batch's instruction;
   flagging the size so the diff is not misread.
4. The legacy per-property score route (`/api/v1/properties/{unit_id}/living-score`) is
   still in the contract and still gated by `ENABLE_LEGACY_ROUTES`. The new estate score
   lives only under `/api/v1/analytics/`, and a test asserts that no other
   `living-score` path appeared.

## Written but not run

- The **Windows Task Scheduler job** itself: out of scope by the batch. Documented as the
  hook in `docs/LIVING_SCORE_V1.md` §6.
- The CLI's printing path was exercised in tests through `cli.main()`; a real
  `python -m app.cli recalc-living-scores` run against `valora_db` was **not** performed,
  because that would write snapshots into the developer's working database.

## Remaining / open questions

- **D6** — security is scored on the raw incident count with no size normalisation,
  because the source spec gives no rule. Sizing that benchmark is a future engine version.
- Cleanup: `docker exec valora_db psql -U valora_user -d valora_db -c "DROP DATABASE valora_test_batch7c;"`
  when the disposable database is no longer wanted. It was left in place so the run is
  reproducible. (Not run: dropping a database is destructive and was not requested.)
- The working tree is dirty by design; nothing was committed or pushed.
