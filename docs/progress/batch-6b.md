# BATCH 6B — intentionally limited security incidents (Task 6, part 2)

Session: 2026-10-10. Branch `valora-work`. One additive migration, one new module set, one test file.
Nothing was committed.

Skills read before coding: `valora-session-protocol`, `valora-testing`, `valora-security-review`,
`valora-migration-safety`, `valora-api-contracts`, `valora-architecture`, `valora-domain-model`,
`valora-data-strategy` (`.agents/skills/` and the account skill files under
`C:\Users\garah\Downloads\skills`), plus `docs/progress/batch-6a.md`. `CLAUDE_README.md`,
`ARCHITECTURE_AND_DOMAIN.md` and `DEVELOPMENT_AND_VALIDATION.md` **still do not exist in this tree**
(only `AGENTS.md` references them), as reported in AI-1..AI-4, PILOT-1 and 6A.

Starting point: `alembic heads` reported `b8e5f2d1c3a4 (head)`, a single head. There were **zero**
matches for "incident" anywhere in `app/`, `alembic/versions/` or `tests/` — this is greenfield, not
a repair. 6A (announcements) was in the tree as required.

## What was built

| Item | File |
| --- | --- |
| 1. Vocabulary (dependency-free) | `app/community/domain/incident_vocabulary.py` |
| 2. Migration (new head) | `backend/alembic/versions/a7c1e9d4f6b2_add_security_incidents.py` |
| 3. Model + registration | `app/community/models/security_incident.py`, `app/db/database.py` |
| 3. Repository | `app/community/repositories/security_incident_repository.py` |
| 4. Service | `app/community/services/security_incident_service.py` |
| 5. DTOs | `app/community/schemas/security_incident.py` |
| 5. Endpoints | `app/community/api/incidents.py`, registered in `app/community/api/router.py` |
| Tests | `backend/tests/test_security_incidents.py` |

Deliberately absent, per the batch's purpose: no description column, no assignment, comment,
attachment, notification or workflow column or endpoint, no `delete` method on the repository, and
no DELETE route. Tests assert all three absences.

**Constraints are generated from the vocabulary.** The model's check constraints and the migration's
check constraints both call `sql_in(...)` on the same tuples, so a value cannot be added in one place
only. `test_check_constraints_are_built_from_the_vocabulary` and
`test_the_migration_builds_its_constraints_from_the_vocabulary` (which greps the migration for
hardcoded values) both guard this.

**`count_in_window(estate_id, start, end)`** counts `start <= occurred_at < end`, status-agnostic,
estate-scoped — the Living Score security input. Half-open deliberately, so adjacent windows tile
without double-counting an incident on a boundary.

**Role-dependent fields.** `property_id`, `resolution_notes` and `created_by` are null for anyone who
is not an estate admin; the keys stay present, following the complaint-anonymity pattern.

## Tests: 48 passing, 8 written-but-not-run

| Layer | Tests | Runs today? |
| --- | --- | --- |
| Vocabulary, model, migration contract, DTOs, route shape, query shape, service policy | 48 | **yes — all passing** |
| Isolation against a real database (`@pytest.mark.integration`) | 8 | **no — skipped, `TEST_DATABASE_URL` unset** |

The running tests cover every item on the batch's test list except the cross-estate claims, which are
integration-only by `valora-testing` (*"fakes built with `Class.__new__` cannot prove tenant
isolation"*). Specifically they pin: the exact vocabulary tuples and helpers; no duplicate/blank/
uppercase values; the vocabulary importing nothing from `app`; the table shape and nullability; the
three FK delete actions (`RESTRICT` / `SET NULL` / `SET NULL`); the four named check constraints; both
indexes; the migration importing the vocabulary rather than hardcoding it; `extra="forbid"` on both
request DTOs; the update DTO exposing only severity/status/notes; out-of-vocabulary values rejected;
the response DTO's exact field set in **serialization** mode (`id`, not `incident_id`); the four route
methods and the absence of DELETE in both the route table and the repository; the service refusing a
resident; create starting `open` with the admin as author; a future `occurred_at` rejected and a
two-minute skew accepted; UTC normalisation; a property from another estate 404-ing; all four
transition cases including terminal `resolved`; the estate-scoped read on update; field hiding for
members and not for admins; and `count_in_window`'s boundary plus its estate scoping — the last proven
by **executing the repository's own compiled SQL** against a real in-memory SQLite table holding rows
one second before the window, exactly at the start, inside, exactly at the end, and one from another
estate (stdlib `sqlite3`, no new dependency).

The 8 written-but-not-run tests carry the cross-estate claims: listing estate B as an estate-A-only
member (403); an estate-B incident id claimed as estate A (404); `hoa_admin` without membership
refused on create and patch (403); resident refused (403); the member response hiding the three admin
fields while the admin response keeps them (asserted at the JSON level, keys present and null);
resolved-then-409 over HTTP; `count_in_window` estate isolation with both statuses counted and an
out-of-window row excluded; and a patch carrying `estate_id` being a 422 with the row unchanged.

## Failing test first, and proof the suite has teeth

1. **Written first:** the first run was **exit 2 — `ImportError: cannot import name
   'incident_vocabulary'`**, i.e. the failing test came before any implementation.
2. **First implementation run was green** (48 passed, 8 skipped). A suite that passes immediately is
   worth distrusting, so I mutated the code twice and confirmed the tests catch it:
   * `occurred_at >= start` → `> start` in `count_in_window`: **`test_count_in_window_is_inclusive_of_the_start_and_exclusive_of_the_end` FAILED**.
   * `if not is_estate_admin:` → `if False:` in `_to_response`: **`test_a_non_admin_response_hides_the_admin_only_fields` FAILED**.
   Both files were restored from backups and verified byte-identical afterwards (`diff` clean), then
   the suite was re-run green.
3. **No shadowed tests.** 6A shipped a silent duplicate test name, so this file was checked the same
   way: `grep -o "def test_..." | sort | uniq -d` is empty, and `--collect-only` reports 56 tests,
   exactly 48 + 8.

## Verification — exact commands and results

Run from `backend/` with `venv\Scripts\python.exe`, `set -o pipefail` on every pipeline:

| Command | Result |
| --- | --- |
| `pytest tests/test_security_incidents.py -q` **before implementing** | **exit 2**, `ImportError: cannot import name 'incident_vocabulary'` |
| `pytest tests/test_security_incidents.py -q` after implementing | **48 passed, 8 skipped** (10.45s) |
| `pytest tests/test_security_incidents.py -q --collect-only` | **56 tests collected** |
| `pytest tests -q -p no:cacheprovider` (whole suite) | **356 passed, 21 skipped** — the 308/13 measured after 6A plus this batch's 48 and 8 |
| `compileall -q app tests scripts` | exit 0 |
| `flake8 app tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | **0** |
| `alembic -c alembic.ini heads` | **`a7c1e9d4f6b2 (head)`**, single head |
| `alembic -c alembic.ini upgrade head --sql` | exit 0; `CREATE TABLE security_incidents` inspected line by line — `incident_id SERIAL PRIMARY KEY`; `estate_id INTEGER NOT NULL`; `property_id INTEGER` and `resolved_at`/`resolution_notes`/`created_by` nullable; `status VARCHAR(20) DEFAULT 'open' NOT NULL`; `occurred_at TIMESTAMP WITH TIME ZONE NOT NULL`; the three named FKs (`RESTRICT`, `SET NULL`, `SET NULL`); `ck_..._category/severity/status` carrying the vocabulary values; `ck_security_incidents_resolution_timestamps CHECK ((status = 'resolved') = (resolved_at IS NOT NULL))`; `created_at`/`updated_at` `DEFAULT now() NOT NULL`; and both indexes |
| `alembic -c alembic.ini downgrade head:b8e5f2d1c3a4 --sql` | exit 0; drops both indexes then the table |
| `git diff --check` | exit 0 |

**Skips are not passes.** All 21 skips need `TEST_DATABASE_URL`, which is unset; 8 are this batch's
isolation tests, 11 are 6A's, 2 pre-date both. **No database was touched and the migration was not
applied to one** — the schema is verified as generated DDL, as compiled SQL and as model inspection
only. No provider was contacted, no key or token read, nothing committed or stashed.

## Deviations from the batch

1. **`size`, not `page_size`.** The batch says "existing style (page/page_size <= 100)". Both exist in
   this tree: the legacy `listings`/`sales` routers use `page_size`, while every modern community
   collection (`complaints`, `work-orders`, `announcements`) and the API-contracts skill use
   `page`/`size` with a max of 100. I used the shared `PaginationParams` (`page`, `size`), so
   `/api/v1/incidents` matches its siblings rather than the deprecated legacy routes. The bound
   requirement is met exactly.
2. **A future `occurred_at` is a 422, not a 409.** The batch does not say which. The check lives in
   the request DTO's validator (with a 5-minute skew), which is where this codebase puts input rules
   (`ComplaintCreate`'s priority pattern, `RegisterRequest`'s password rule) and which yields the
   correct HTTP semantics. A service-level duplicate was deliberately not added: it would be
   unreachable through the API and therefore untestable.
3. **Patching an immutable field is a 422, not a silent no-op.** `extra="forbid"` (required by the
   batch) means sending `category`, `occurred_at`, `estate` or `property_id` in a PATCH body is
   refused outright. The integration test asserts exactly that.
4. **`resolved` is fully terminal**, including `resolution_notes` and repeat `status: "resolved"`
   calls, which is the strictest reading of "terminal (409 on further change)". See open question 1 —
   this is the batch's flagged question and I chose the strict side deliberately.
5. **`incident_vocabulary.py` defines its own `sql_in`** rather than importing
   `triage_vocabulary`'s. The batch required "dependency-free", and a test enforces it (no `from app.`
   in the file). The duplication is six lines; see open question 3.
6. **`tasks/todo.md` was not touched.** 6A was told not to tick Task 6; 6B does not mention it. Both
   halves of Task 6 are now implemented, but 19 of the cross-estate tests are still unrun, so I left
   the claim to a human — see open question 5.

## Open questions

1. **Should a resolved incident be fully frozen?** Today a typo in `resolution_notes` cannot be
   corrected, and a repeat `status: "resolved"` is a 409 rather than an idempotent no-op. The
   alternative is to allow notes edits (or idempotent same-status patches) while keeping the status
   and `resolved_at` frozen. The batch asked for this to be listed; it needs a product answer.
2. **A mis-typed `occurred_at` or `category` has no correction path.** The batch makes both immutable
   and there is no delete, which is right for history but leaves an operator who mis-dates an incident
   with no fix at all. Options: an admin-only correction window, a superseding record, or accepting it
   and relying on the operator. Worth deciding before the pilot, because the Living Score reads this
   field.
3. **Extract the shared check-constraint renderers?** `sql_in`/`nullable_sql_in` now exist in
   `triage_vocabulary` and `incident_vocabulary`. A single `app/common/sql_constraints.py` would be
   DRY, but it touches a stable module — deferred rather than done opportunistically.
4. **Should an incident link to a complaint?** A theft may also be reported as a complaint, and today
   the two are unrelated records of the same event, so the score counts it once (good) but the HOA
   sees two. No link column was added because the batch defines incidents as score inputs only.
5. **Task 6 could be ticked** now that announcements and incidents both exist, but 19 DB-backed
   isolation tests across 6A and 6B have never run. My recommendation: run the integration pass first,
   then tick all three boxes.
6. **The Security sub-score still has no data in a real estate.** `count_in_window` exists and is
   tested, but nothing calls it yet — Task 7 is unbuilt, and per `docs/ADR-005-Living-Score-Authority.md`
   it is the next batch. Until then the table will be empty unless a pilot admin records incidents.
7. **No retention or volume policy.** Incidents are append-only with no pruning; at pilot scale that is
   fine, but the table has no archive story, unlike the `ai_call_events` ledger's known gap.
8. Unchanged from earlier sessions: root-level `CLAUDE_README.md`, `ARCHITECTURE_AND_DOMAIN.md` and
   `DEVELOPMENT_AND_VALIDATION.md` still do not exist, and `docs/PROJECT_STATUS.md` still overstates the
   analytics entity inventory (noted in `docs/progress/score-authority.md`).

## Files changed

| File | Change |
| --- | --- |
| `app/community/domain/incident_vocabulary.py` | **new** |
| `app/community/models/security_incident.py` | **new** |
| `app/community/repositories/security_incident_repository.py` | **new** |
| `app/community/schemas/security_incident.py` | **new** |
| `app/community/services/security_incident_service.py` | **new** |
| `app/community/api/incidents.py` | **new** |
| `backend/alembic/versions/a7c1e9d4f6b2_add_security_incidents.py` | **new** (the new head) |
| `app/community/api/router.py` | added `include_router(incidents_router)` |
| `app/db/database.py` | added the model import to the Alembic registry |
| `backend/tests/test_security_incidents.py` | **new** (56 tests) |
| `docs/progress/batch-6b.md` | **new** (this note) |

No existing migration was edited, no unrelated file was touched, and `tasks/todo.md` is unchanged.
