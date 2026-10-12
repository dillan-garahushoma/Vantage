# PILOT-1 — provision a real pilot estate and measure AI usage

Session: batch PILOT-1 (independent of the AI batches; assumes Task 6 done).
Status: **complete**. Nothing was run against a real database, and nothing was
committed.

## Done

| Deliverable | Path | State |
| --- | --- | --- |
| Provisioning CLI (argparse, dry-run by default) | `backend/scripts/provision_estate.py` | written, exercised by tests |
| Read-only AI usage report | `backend/scripts/ai_pilot_report.py` | written, exercised by tests |
| Operator runbook + POPIA checklist | `docs/PILOT_RUNBOOK.md` | written |
| Tests | `backend/tests/test_provision_estate.py`, `backend/tests/test_ai_pilot_report.py` | 44 tests, all passing |

`provision_estate.py`

- Dry-run by default; `--apply` is the only way to write. `--expect-database NAME`
  and a demo-database name guard (`*demo*`, `*seed*`, `*sample*`, `*scratch*`,
  overridable only with `--allow-demo-database`) both refuse the run before
  anything is written.
- Always prints `host:port/database` with the password redacted, first, before
  any plan or write. `DATABASE_URL` is read from the environment only — never
  from `.env` — so the printed target is provably the target.
- `estate --file estate.json`: creates the estate with `is_demo=False`, its
  units (`Property`), HOA admin users, service-provider users **and** their
  `ServiceProvider` profiles with `user_id` set, plus estate memberships for
  each. Idempotent: a second run creates nothing and reports what it skipped.
- `link-resident --estate-id --email --unit-no` and
  `link-residents-csv --estate-id --file residents.csv` (columns `email,unit_no`)
  create `resident` memberships with `property_id` set. Warnings when the
  account's self-declared `unit_no` differs, when the resident is already linked
  to another unit, and errors (exit 1, row skipped) for an unknown email or unit.
- Passwords are generated with `secrets` (24 chars, alphanumeric), printed once
  to stdout under `--apply` only, hashed with the app's `hash_password`, and
  never logged.
- No new dependencies. The older version of this script on disk before this
  session was rewritten cleanly; `app/seed_demo.py` and its CLI were not touched.

`ai_pilot_report.py`

- Read-only by construction: the module can only send the three `SELECT`
  statements returned by `read_only_statements()`, and a test asserts every one
  of them starts with `SELECT`. No INSERT/UPDATE/DELETE exists in the file.
- Reads only the metadata-only tables from AI-2/AI-3 — `ai_call_events` and
  `complaint_ai_suggestions`. Neither has a prompt/response/text column, and a
  test asserts no statement even mentions such a word, so the report cannot
  print resident-written text or provider output.
- Prints calls by feature/status/reason with `n` of timed calls, average and p95
  (nearest-rank) latency; triage accepted/overridden/dismissed counts and rates
  with `n` shown and an explicit "n < 30 is not meaningful" note; and the Health
  Brief section, which is skipped with a clear message until AI-4.
- A table that does not exist is skipped with a message naming the table and the
  `alembic upgrade head` remedy, and the run still exits 0. When no AI table
  exists at all it says so rather than printing zeroes, which would read as "no
  usage".
- `--estate-id` (required) and `--days` (positive, default 30). The window is a
  bound parameter; nothing is string-interpolated into SQL.

`docs/PILOT_RUNBOOK.md` covers: demo vs pilot separation; env vars and secret
handling; the flag-enabling order (`AI_INSIGHTS_ENABLED` first; `AI_TRIAGE_ENABLED`
and `AI_PERSONAL_DATA_ALLOWED` only after the provider-terms and POPIA
sign-off); the kill switch (`AI_ENABLED=false` **plus a restart**, because
settings are cached at import); backup/restore commands marked documented-not-run;
resident onboarding steps; the POPIA checklist marked as a checklist for lawyer
review, not legal advice; and a NOT READY list.

## Tests added and passing

44 new tests across the two files (23 + 21):

- `test_provision_estate.py` (23): dry run writes nothing and prints no password;
  the target database is printed first without credentials; apply creates the
  estate, units, users, provider profile and memberships; role/membership
  correctness through the real `EstateAuthorizationService.resolve_access` (HOA
  admin, estate provider, non-member → 403); the provider profile is found by the
  real `ServiceProviderRepository.get_by_user_id`, which is what
  `WorkOrderService.create_work_order` requires (it refuses a NULL `user_id`);
  apply is idempotent; a unit number owned by another estate stops the run; a
  legacy unit with no estate stops the run; duplicate unit numbers in the file
  stop the run; passwords are printed once and never appear in log records;
  demo-database and `--expect-database` guards refuse; malformed JSON is reported
  not crashed; resident linking, its idempotency, the mismatched-unit warning, an
  unknown email, and both CSV paths.
- `test_ai_pilot_report.py` (21): grouping by feature/status/reason; p95
  nearest-rank and its behaviour on small samples; untimed calls counted but not
  averaged; triage counts, rates, `n`, the sub-30 note, and the empty case; every
  section rendered from an injected session; each missing table skipped with a
  clear message; the Brief section skipped until AI-4; read-only asserted against
  the recorded statements and the module's statement list; no prompt/response/
  text word in any statement; `--days` bound as a parameter; `--estate-id`
  required (argparse fails before any connection opens); an empty ledger reports
  zero calls; redaction and `--days` validation.

## Written, not run

- **No database was touched, by any script.** The tests drive the real CLI code
  through injected fake sessions, so "dry-run writes nothing", "apply is
  idempotent", "collision stops" and "read-only" are assertions about the scripts
  and the SQL they build, not about a live PostgreSQL database.
- The real `INSERT`s (estate, units, users, provider profiles, memberships) and
  the real `SELECT`s (ledger, suggestions, `information_schema` table check) were
  never executed against PostgreSQL. `alembic upgrade head` was **not** run
  against any database.
- Nothing in `docs/PILOT_RUNBOOK.md` section 5 (pg_dump/pg_restore) was run.
- `provision_estate.py` and `ai_pilot_report.py` were never executed end to end
  as `python scripts/...` with a real `DATABASE_URL`.
- Integration tests: `TEST_DATABASE_URL` is not set in this shell, so the suite's
  2 integration tests **skipped**. A skip is not a pass; nothing here was
  verified against a test database.

## Checks run (with results)

```text
backend/venv/Scripts/python.exe -m pytest backend/tests -q -p no:cacheprovider
  → 290 passed, 2 skipped, 3 warnings in 160.50s
     (baseline before this batch: 246 passed, 2 skipped; +44 new tests here.
      The 2 skips are the unset TEST_DATABASE_URL integration tests, not passes)

backend/venv/Scripts/python.exe -m compileall -q app scripts tests      → exit 0
backend/venv/Scripts/python.exe -m flake8 app tests scripts \
    --count --select=E9,F63,F7,F82 --show-source --statistics           → 0, exit 0
backend/venv/Scripts/python.exe -m alembic -c alembic.ini heads
  → b8e5f2d1c3a4 (head)                                                → exit 0
backend/venv/Scripts/python.exe -m alembic -c alembic.ini upgrade head --sql
  → exit 0, 19 CREATE TABLE statements, head unchanged                 → exit 0
git diff --check                                                        → exit 0
```

## No migration needed (as the batch expected)

`alembic heads` is still `b8e5f2d1c3a4` — the AI-3 suggestion table — and the
offline `upgrade head --sql` replays the existing chain unchanged. This batch adds
scripts and docs only. The ledger and suggestion tables already exist from
AI-2/AI-3, and `estates.is_demo` already exists from AI-2.

## Deviations and findings in the real tree

1. **`Property.unit_no` is not globally unique.** The batch says it is. In the
   real tree the hardening migration `d4a7e1c9b3f2` replaced the global unique
   with `uq_properties_estate_unit_no` (per estate) plus a partial unique index
   for legacy rows where `estate_id IS NULL`. The script therefore does something
   **stricter** than the database: it refuses to reuse a unit number that exists
   in *any* other estate, stops the whole run, and reports which estate owns the
   number. The constraint itself was not altered.
2. **`hoa_approved` and `email_verified` gate nothing.** Verified by search: they
   appear only in `app/identity/domain/entities.py`, `app/identity/schemas/auth.py`
   and `app/seed_demo.py`. Login checks the password only. The script sets both to
   `true` for provisioned accounts so the DTO describes an operator-provisioned
   user correctly; **no authorisation decision depends on them**, and the runbook
   says so. This is the honest answer to "set only what is needed": today, neither
   is needed for anything.
3. **The Health Brief section is skipped, not faked.** No `health_brief*` table
   exists anywhere in the repo, so the report says the tables arrive in AI-4 and
   skips the section rather than reporting zeroes. If those tables ever exist, the
   report says it does not read them yet because AI-4 owns their shape.
4. **Password generation rule.** `secrets.choice` over an alphanumeric alphabet,
   24 characters, matching the app's bcrypt max-72-byte limit. Printed once, on
   `--apply` only.
5. **"stdlib only, no new deps" means no *new* dependency, not no library.** Both
   scripts use SQLAlchemy and asyncpg from the existing venv, which is how every
   other database access in this project works. `argparse`, `secrets`, `csv`,
   `json` and `urllib.parse` are stdlib; no package was added to
   `requirements.txt`.
6. **The report does not call `AICallEventRepository`.** That repository exposes
   only `record` (append) and `count_since`/`count_statement` (the budget guard's
   count); there is no list-for-estate read to build a per-feature report from.
   Adding one would have been new service surface outside this batch, so the
   report sends its own estate-scoped `SELECT` that mirrors `count_statement`'s
   scoping (`estate_id = :estate_id AND created_at >= :since`) with the estate id
   as a bound parameter. The table and column names it reads are the existing
   AI-2/AI-3 ones.

## Remaining / not in this batch

- No migration was needed, so none was written.
- No changes to `app/seed_demo.py`, the demo database, or any applied migration.
- The pilot needs the AI-4 tables before the Brief rows in the report become real.
- The runbook's NOT READY list is the operator's to-do list: password reset,
  membership approval/invitations, TLS/hosting, monitoring, email.

## Open questions for the human

1. **Should the pilot use `ENVIRONMENT=pilot`?** The config validation only
   special-cases `development`, so anything else tightens `SECRET_KEY` checks —
   which is what we want, but it means the pilot's `SECRET_KEY` must be ≥ 32
   chars and not a known placeholder.
2. **Is `AI_DAILY_CALL_CAP_PER_ESTATE=200` the right pilot budget?** It is the
   code default. A real estate's complaint volume should decide it, and the report
   will show `rejected_budget` rows when it is too low.
3. **Who is the information officer for the pilot?** The POPIA checklist cannot
   be signed off without a named person; that is a business decision, not a code
   change.
4. **Should unit numbers be reusable across estates?** The script's stricter rule
   is deliberate and safe for a pilot, but if a second real estate legitimately
   uses the same numbering scheme, the rule needs revisiting (the database itself
   would allow it).
