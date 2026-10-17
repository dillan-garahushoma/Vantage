# BATCH 7B — Snapshot persistence, input aggregation, calculation service

**Date:** 2026-10-11 · **Scope:** one additive migration, one model, two repositories,
one service, one domain vocabulary module. **No endpoints.** Legacy
`LegacyPropertyScore*` untouched.

## Prerequisites (verified before writing code)

- **7A** is in the tree: `app/analytics/engine/` with `calculate_living_score`,
  `window_bounds`, `EstateScoreInputs`, `ScoreResult` (43 tests green).
- **6B** is in the tree: `security_incidents` + `SecurityIncidentRepository.count_in_window`.
- **Migration head was `a7c1e9d4f6b2`** (6B's revision), confirmed with
  `alembic heads`, so this batch's migration revises it directly.

## Done

| File | Contents |
|---|---|
| `backend/app/analytics/domain/snapshot_vocabulary.py` | Dependency-free status vocabulary + the two check-constraint bodies, shared by the model and the migration (mirrors 6B's `incident_vocabulary.py`). |
| `backend/app/analytics/models/living_score_snapshot.py` | `LivingScoreSnapshot` — all 17 columns, named constraints, `(estate_id, as_of DESC)` index. |
| `backend/alembic/versions/c4d8f1a7b9e3_add_living_score_snapshots.py` | Additive `upgrade`, working `downgrade`. |
| `backend/app/analytics/repositories/living_score_snapshot_repository.py` | `add`, `latest_for_estate`, `history`, `count` + pure statement builders. **No update, delete, save or upsert.** |
| `backend/app/analytics/repositories/living_score_inputs_repository.py` | The aggregate SQL that produces `EstateScoreInputs`. |
| `backend/app/analytics/services/estate_living_score_service.py` | `LivingScoreService.calculate_and_snapshot`, `latest`, `history`. |
| `backend/app/db/database.py` | One line: registers the new model so `Base.metadata` is complete. |
| `backend/tests/test_living_score_snapshots.py` | 80 tests, written first (first run: `ImportError`, exit 2). |

### Migration

`living_score_snapshots` exactly as specified: `snapshot_id` PK; `estate_id` NOT NULL
FK **RESTRICT**; `engine_version` varchar(20); `as_of`/`window_start` timestamptz;
`calculated_at` timestamptz default now(); `calculated_by` FK users **SET NULL**;
`status` varchar(20) + vocabulary check; `overall_score` NUMERIC(5,2) NULL;
`measured_weight` NUMERIC(4,2) NOT NULL; the five component scores NUMERIC(5,2) NULL;
`inputs`/`explanation` JSONB NOT NULL; bounded-scores check; status/overall
equivalence check; index `(estate_id, as_of DESC)`. There is deliberately **no**
`updated_at`, because a corrected score is a new snapshot, never an edit.

Verified against the real database (not just offline SQL) — `upgrade head`, then
`information_schema`/`pg_constraint`/`pg_indexes`, then `downgrade a7c1e9d4f6b2`,
then `upgrade head` again:

```
snapshot_id integer NOT NULL | estate_id integer NOT NULL | engine_version varchar NOT NULL
as_of timestamptz NOT NULL | window_start timestamptz NOT NULL | calculated_at timestamptz NOT NULL
calculated_by integer null | status varchar NOT NULL
overall_score numeric(5,2) null | measured_weight numeric(4,2) NOT NULL
resolution_score/frequency_score/security_score/satisfaction_score/infrastructure_score numeric(5,2) null
inputs jsonb NOT NULL | explanation jsonb NOT NULL
constraints: ck_..._scores_bounded, ck_..._status, ck_..._status_matches_overall,
             fk_..._calculated_by_users, fk_..._estate_id_estates, living_score_snapshots_pkey
index: CREATE INDEX ix_living_score_snapshots_estate_id_as_of ... (estate_id, as_of DESC)
downgrade -> table present after downgrade: 0 ; re-upgrade -> running upgrade a7c1e9d4f6b2 -> c4d8f1a7b9e3
```

## Tests added and passing

`backend/tests/test_living_score_snapshots.py` — **80 passed**.

**Without `TEST_DATABASE_URL`: 71 passed, 9 skipped.** The 9 skips are this batch's
`@pytest.mark.integration` tests; they are reported as **not run**, never as passes.

**With `TEST_DATABASE_URL=...valora_test`: 80 passed** — the 9 integration tests
really executed against PostgreSQL, which is the only place the aggregation SQL,
the constraints and tenant isolation are actually proven.

Coverage, per the batch list: compiled SQL of **every** aggregate contains the
`estate_id` filter and both window bounds (the one unwindowed input, `unit_count`,
is asserted separately); cross-estate isolation and legacy NULL-estate exclusion in
a real database; the service persists **exactly one** snapshot with
`engine_version == "1.0.0"` and the aggregates it consumed; the same data and
`as_of` produce identical numbers (fake-driven and end-to-end through PostgreSQL);
the insufficient case stores `NULL` overall with `status = "insufficient_data"` and
NULL component scores; a resident, and a global admin without membership, are both
refused; `as_of` is read **once** (monkeypatched counter) and an explicit `as_of`
never touches the clock; **no UPDATE/DELETE** is issued against the snapshot table
(sourced scan: no such method exists, no update/delete is built in the module; plus
a `before_cursor_execute` listener asserting only SELECT/INSERT during
calculate → latest → history); migration offline SQL **both ways**.

Beyond the list, the migrated schema was asked to reject nonsense directly: a
`scored` row with no overall score, an `insufficient_data` row claiming 50, scores
of 101 and −1, a status outside the vocabulary, and an estate that does not exist
are each refused by PostgreSQL, while the honest combination is accepted — proving
the constraints exist in the database and do not simply reject everything.

### Mutation check (proving the suite has teeth)

Each mutation was applied, a targeted test run, and the file restored immediately
(`diff` against a backup confirmed clean afterwards):

| Mutation | Result |
|---|---|
| Ratings aggregate loses its `estate_id` filter | 3 failed |
| Coverage clamp 90 → 3650 | 2 failed |
| Incidents window end no longer inclusive (`end` instead of `end + 1µs`) | 1 failed |
| Service stops committing | 1 failed |
| `status = 'scored' ⇔ overall IS NOT NULL` check weakened to `true` | 1 failed |

**One real bug was found by the database test, not by the fakes.** The
work-order *count* was being unpacked through the same helper as the *averages*, so
`work_orders_completed` reached the engine as `Decimal` and serialised into the
snapshot as the string `"3"`. The fake-driven test passed anyway, because
`Decimal("6") == 6` is true in Python — only the JSON assertion over real rows
exposed it. Fixed with a separate `_counts()` helper so counts stay `int`; the
batch's test for it now asserts the JSON value is a number.

## Decisions taken where the batch was silent (all kept deliberate and tested)

- **D-1 — The incidents boundary.** 6B's `count_in_window` is half-open
  (`start <= occurred_at < end`) while 7A's window is inclusive at both ends
  (decision D1). The batch says to use 6B's helper *and* 7A's `window_bounds`, so
  the helper is called with `end + 1 microsecond` — the smallest step `timestamptz`
  can store — which makes the incident count inclusive exactly as the engine's own
  `in_window` is. Tested by asserting the exact bounds the helper receives; an
  incident sitting precisely on `as_of` is counted.
- **D-2 — Resolution is averaged in SQL, converted in Python.** `avg(extract(epoch
  from resolved_at - created_at))` yields exact seconds; dividing by `Decimal(86400)`
  in Python keeps the engine's Decimal-only rule without a DB-specific interval type.
- **D-3 — "Completed" means `status = 'completed'`**, and the ratings window is
  keyed on `resolved_at`, which `work_order_service` sets as the completion instant.
- **D-4 — Provider ratings deduplicate providers** via a `SELECT DISTINCT
  provider_id` subquery before joining `service_providers`, so a provider with five
  window jobs counts once and the mean is not weighted by repeat business.
- **D-5 — Reads allow any estate member, not just admins.** The batch specifies
  *membership* for `latest`/`history`; a resident of the estate can read, and only
  `calculate_and_snapshot` requires `hoa_admin` globally **and** a matching
  membership.
- **D-6 — The service lives in `estate_living_score_service.py`** so it cannot be
  confused with `living_score_service.py`, which holds `LegacyPropertyScoreService`.
- **D-7 — `add` flushes, the service commits once** (AGENTS.md): the whole
  gather → engine → persist use case is one transaction.

## Written but not run / not reachable

- **The CLI path (`actor=None`) has no caller yet.** It is implemented and tested
  at the service level, but no command-line entry point invokes it in this batch.
  It is provably not reachable from HTTP: a test walks every `.py` under `app/` and
  asserts nothing outside the service module references `LivingScoreService`.
- Nothing else: every artifact in this batch was executed by the commands below.

## Pre-existing defect found (NOT caused by this batch)

`backend/tests/factories.py` passes `hoa_approved=True` to
`UserRepository.create()`, whose signature does not accept it. Both files are
**tracked and unmodified** (`git status` clean), so HEAD itself is internally
inconsistent.

Consequence: with `TEST_DATABASE_URL` set, **19 DB-backed tests in other batches
fail** before asserting anything — 8 in `test_security_incidents.py` (6B) and 11 in
`test_announcements_estate_scoping.py` — each with the identical
`TypeError: UserRepository.create() got an unexpected keyword argument 'hoa_approved'`
(19 failures, 19 occurrences). Without `TEST_DATABASE_URL` they skip, which is why
this was never visible.

This batch does **not** depend on that helper: its integration tests seed their own
two-estate world directly through the ORM, so its 80 tests pass regardless. I did
not repair `factories.py` or `UserRepository` — that is unrelated identity code
(subject to the "never touch unrelated changes" rule) and the right fix is a human
decision, not a coding one.

## Commands run, with results

```
alembic heads                                     -> c4d8f1a7b9e3 (head)
alembic upgrade head            (valora_test)     -> ok
alembic downgrade a7c1e9d4f6b2  (valora_test)     -> table gone
alembic upgrade head            (valora_test)     -> ok

pytest tests/test_living_score_snapshots.py -q                    -> 71 passed, 9 skipped
pytest tests/test_living_score_snapshots.py -q  (TEST_DATABASE_URL) -> 80 passed
pytest tests -q                                 (TEST_DATABASE_URL) -> 481 passed, 19 failed
  (all 19 are the pre-existing factories/UserRepository mismatch above; no 7B test fails)

python -m compileall -q app                       -> OK
flake8 app tests --select=E9,F63,F7,F82 --count   -> 0
flake8 app/analytics <new files> --max-line-length=120 -> 5 x W391, all on pre-existing
  app/analytics/*/__init__.py files (tracked and unmodified); new files clean
git diff --check                                  -> clean
```

Only `backend/app/db/database.py` is a **modified** tracked file (one registry
line). Everything else this batch added is new. `LegacyPropertyScore*` is
unmodified, and nothing in `app/` outside the service module references the new
service — no endpoint was registered, as the batch requires.

## Remaining (deliberately out of scope)

- Any HTTP surface for the score (the batch says "no endpoints"): a read-only
  latest/history route under the estate-scoped, membership-guarded pattern, with
  DTOs — models are never API DTOs.
- A CLI/backfill command that exercises the `actor=None` path.
- Re-issuing BATCH AI-4 (the AI Health Brief), which has been waiting on exactly
  these field names since ADR-005.

## Open questions

1. **Security size normalisation is still open** (7A decision D6). The snapshot now
   stores the raw incident count against the 0–15 benchmark, which penalises large
   estates. Changing it is a v1.1.0 engine version writing *new* snapshots.
2. **`coverage_days` is derived from `estates.created_at`.** An estate created
   years ago but onboarded last week is treated as having full coverage. A
   "when did data start" signal (first complaint/incident, or an onboarding date)
   would be more honest — worth a product decision.
3. **Who may see a score?** This batch lets any member read (the batch specified
   membership). Residents seeing an estate-wide health index is a product choice,
   and if the answer is "admins only" the read guard is a one-line change.
4. **The 19 pre-existing DB test failures** (above) need a human call: restore
   `hoa_approved` on `UserRepository.create`, or drop it from `factories.py`.
