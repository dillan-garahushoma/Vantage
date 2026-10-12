# BATCH 6A — estate-scoped announcements (Task 6, part 1)

Session: 2026-10-10. Branch `valora-work`. **No production code was changed and no migration was
added.** One new test file. Nothing was committed.

Skills read before starting: `valora-session-protocol`, `valora-testing`, `valora-security-review`,
`valora-migration-safety`, `valora-api-contracts`, `valora-architecture`, `valora-domain-model`
(from `.agents/skills/` and the account skill files under `C:\Users\garah\Downloads\skills`), plus
`docs/progress/*` and `docs/ADR-004-AI-Assist-Layer.md`. `CLAUDE_README.md` and
`ARCHITECTURE_AND_DOMAIN.md` still **do not exist in this tree** (only `AGENTS.md` references them),
as reported in AI-1..AI-4 and PILOT-1 — so the batch was run from `AGENTS.md` plus the skills.

Starting point: `git status` and `git diff --stat` showed the pre-existing dirty tree from
Phase 1 / AI-1..AI-4 / PILOT-1; `alembic heads` reported `b8e5f2d1c3a4 (head)`, a single head.
(`backend/docker-compose.yml` and `backend/Dockerfile` are dirty in this tree but were already dirty
when this session started; neither was touched here.)

## 1. Migration — already present, so nothing was added

The batch expected a missing migration for `announcements.estate_id`. **It already exists**, in the
chain, as `e5b8c2f1a4d7_scope_announcements_to_estates.py` (`down_revision = d4a7e1c9b3f2`), and the
revision order is `d4a7e1c9b3f2 → e5b8c2f1a4d7 → f6c9d3a8b2e1 → b8e5f2d1c3a4 (head)`. It does
exactly what the batch asks:

* `estate_id INTEGER NULL` — legacy-safe, no backfill, no `NOT NULL`;
* named FK `fk_announcements_estate_id_estates` → `estates.estate_id` with `ON DELETE RESTRICT`;
* index `ix_announcements_estate_id`;
* a documented, symmetrical `downgrade()`.

Both directions were checked offline (see the command table). Per the batch's own instruction — "If
one already exists, add nothing" — no revision file was created and no applied migration was edited.

## 2. What was actually missing: the tests

There was no announcement test file at all. `backend/tests/test_announcements_estate_scoping.py` is
new, with 29 tests:

| Layer | Tests | Runs today? |
| --- | --- | --- |
| Policy / query shape / HTTP contract (no database) | 18 | **yes — all passing** |
| Isolation against a real database (`@pytest.mark.integration`) | 11 | **no — skipped, `TEST_DATABASE_URL` unset** |

The split is deliberate and follows `valora-testing`: *"Fakes built with `Class.__new__` cannot prove
tenant isolation. Never rely on them for an authorization claim."* Every "estate A cannot touch
estate B" claim is an integration test; the non-database tests cover policy, DTO contracts, query
shape and the HTTP surface only.

What the 18 running tests pin:

1. `list` scopes **both** the `search` and the `count` call to the requested estate.
2. `include_expired` is ignored for a non-admin and honoured for an estate admin.
3. An expired announcement is hidden from a non-admin on `get`, visible to an estate admin.
4. `get` uses **only** `get_by_id_in_estate` — the double raises `AssertionError` if the unscoped
   getter is ever called — and passes the estate id through.
5. `create` takes `estate_id` from the query and `created_by` from the acting admin; a body carrying
   `estate_id: 999, created_by: 999` has no effect on either.
6. `update` cannot move an announcement to another estate (row stays in estate 8, title still
   updates).
7. The request DTOs expose exactly `{title, message, expires_at}`; a payload carrying
   `estate_id`/`created_by` yields nothing at all from `model_dump(exclude_unset=True)`.
8. **Legacy NULL-estate rows.** The repository's own statements are captured and then *executed*
   against a real in-memory SQLite table holding three rows (estate 8, estate 9, and one with
   `estate_id IS NULL`). `search` returns only the estate-8 row, `count` returns 1, and the scoped
   getter for the NULL row returns nothing — so the exclusion is proven by executing SQL, not by
   reading the code. (No new dependency: `sqlite3` is stdlib.)
9. Pagination bounds over HTTP: `page=0`, `size=0`, `size=101`, a missing `estate_id` and
   `estate_id=0` are all 422; `page=1&size=100` is accepted and returns the standard envelope.
10. A resident gets 403 from create, update **and** delete.
11. `create` over HTTP reads `estate_id` from the query (2) and the author from the token (user 77),
    ignoring a body that tries to set both.

The 11 written-but-not-run integration tests cover the full IDOR matrix the batch describes:
listing estate B as an estate-A-only member (403), reading an estate-B announcement id while
claiming estate A (**404**, per the tenancy rule), `hoa_admin` **without** membership writing (403),
resident writing (403), expired hidden from residents and `include_expired=true` ignored for them,
expired visible to the admin, a legacy NULL-estate row invisible in both list and get, create
ignoring body-supplied estate/author, update unable to move the estate, and the estate-A listing
returning only estate-A rows.

## 3. Failing test first, honestly

The first run was **1 failed, 16 passed, 11 skipped**. The failure was in my own double, not in the
app: `_EmptyResult` lacked `scalar_one_or_none()`, so `get_by_id_in_estate` raised `AttributeError`.
I fixed the double (the missing method), **not** the assertion, and re-ran. No assertion was
weakened, skipped, or removed.

A second defect was mine, and it was silent rather than loud: the unit-level and integration tests
for "update cannot change the estate" were both named
`test_update_cannot_move_an_announcement_to_another_estate`, so the later definition **shadowed** the
earlier one at module scope. `pytest --collect-only` then reported 28 tests from 29 definitions, and
the non-skipping version of that test never ran at all. Renamed to
`test_update_service_cannot_move_an_announcement_to_another_estate` and
`test_update_http_cannot_move_an_announcement_to_another_estate`; the module now collects all 29, and
the passing count moved from 17 to 18 because the shadowed test finally executed. Worth knowing that
identical names across the two layers are easy to introduce in a file like this — the check that
caught it was `grep -o "def test_..." | sort | uniq -d`.

After that fix the tests passed unchanged on the first correct run — which is the real result of this
batch: **the behaviour was already implemented**; what was missing was the coverage. I did not invent
a code change to have something to fix. The three things the tests *did* expose as genuine defects are
out of this batch's scope and are listed under open questions instead.

## 4. DELETE is a hard delete — reported, not changed

As instructed, `DELETE /api/v1/announcements/{id}` was not touched. It is a **hard delete**:
`AnnouncementService.delete_announcement` → `AnnouncementRepository.delete` → `session.delete(...)`
+ `commit`. The `announcements` table has no `deleted_at`, no soft-delete flag and no audit trail,
and there is no `announcement_event` history equivalent to `complaint_events`.

This conflicts with the preservation rule in `valora-domain-model` — *"Historical operational data
must never be casually updated in place, overwritten, or deleted"* — which names an audit trail and
soft delete as mandatory for the future ML feature store. **Listed as an open question below.** I did
not pin the hard delete with a test on purpose: a test asserting today's behaviour would make the
obvious fix (soft delete) look like a regression.

## 5. Task 6 was not ticked

`tasks/todo.md` was left untouched. Task 6 ("estate announcements **and security incidents**") is not
complete — security incidents do not exist anywhere in the tree — so ticking it would be a false
claim. The three Task 6 checkboxes remain `[ ]`.

## Verification — exact commands and results

Run from `backend/` with `venv\Scripts\python.exe`, `set -o pipefail` on every pipeline:

| Command | Result |
| --- | --- |
| `pytest tests/test_announcements_estate_scoping.py -q -rs` **first run** | **1 failed, 16 passed, 11 skipped** (the `_EmptyResult` defect above) |
| same file, after fixing the double | **17 passed, 11 skipped** (3.60s) — this is where the name collision was still hiding one test |
| same file, after renaming the two colliding tests (`--collect-only`) | **29 tests collected**; then **18 passed, 11 skipped** (4.63s) |
| `pytest tests -q -p no:cacheprovider --ignore=tests/test_announcements_estate_scoping.py` (baseline) | **290 passed, 2 skipped** — measured here, not assumed |
| `pytest tests -q -p no:cacheprovider` (whole suite) | **308 passed, 13 skipped** — the measured baseline plus this batch's 18 passing and 11 skipping tests, exactly |
| `compileall -q app tests scripts` | exit 0 |
| `flake8 app tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | **0** |
| `alembic -c alembic.ini heads` | `b8e5f2d1c3a4 (head)`, single head |
| `alembic -c alembic.ini history` | `d4a7e1c9b3f2 -> e5b8c2f1a4d7` confirmed in the chain |
| `alembic -c alembic.ini upgrade head --sql` | exit 0; emits `ALTER TABLE announcements ADD COLUMN estate_id INTEGER`, `ADD CONSTRAINT fk_announcements_estate_id_estates ... ON DELETE RESTRICT` and `CREATE INDEX ix_announcements_estate_id` |
| `alembic -c alembic.ini downgrade e5b8c2f1a4d7:d4a7e1c9b3f2 --sql` | exit 0; drops the index, the constraint and the column |
| `git diff --check` | exit 0 |

**Skips are not passes.** All 13 skips are integration tests that require `TEST_DATABASE_URL`, which
is unset in this terminal; 11 of them are this batch's new isolation tests. Every isolation claim in
this batch is therefore **written, not run**.

**No database was touched.** No migration was applied. No provider was contacted. No key, token,
password or invitation code was read, printed or logged. Nothing was committed or stashed.

## Deviations from the batch

1. **Item 1 produced no work**, because the migration already exists. Reported rather than duplicated.
2. **Item 3 produced no work**, because no listed behaviour was missing. I did not manufacture a fix.
3. **Ten of the required behaviours are asserted twice** — once as a database-free policy/HTTP test
   that runs today, and once as an integration test that runs when a test database exists. This is
   deliberate: the batch's list must be verifiable now *and* provable against SQL later, and the
   testing skill forbids using fakes for the isolation claims.
4. **The `pagination bounds` item says `page_size`; this codebase's parameter is `size`** (max 100),
   per `app/common/pagination.py` and the API-contracts skill. The tests assert `size`, the existing
   contract, and assert that `page >= 1` too.
5. **"Neither is accepted in the body" was read as "cannot influence the stored row"**, not "must be
   rejected". Extras are silently ignored today, and that is safe here: the body value is never read,
   and the estate comes from an authorized membership. Making the DTOs `extra="forbid"` would be a
   contract change beyond this batch — see open question 3, where I recommend it for `create` only.

## Open questions

1. **DELETE is a hard delete and the domain-model skill forbids that for operational history.**
   Options: soft delete (`deleted_at` + read filter), an `announcement_events` audit table, or keep
   hard delete and relax the rule for announcements explicitly. The batch deliberately deferred this;
   it should be decided before the pilot, because after launch the deleted rows are simply gone.
2. **A whitespace-only announcement can be created.** Verified: `AnnouncementCreate.model_validate(
   {"title": "   ", "message": "   "})` **succeeds** (`min_length=1` counts spaces), and the service
   then strips both fields, so an announcement with an empty title and empty body is stored. A
   one-line validator (strip, then require non-empty) fixes it. Not in this batch's list, so not
   changed — but it is a real defect, not a style preference.
3. **Should `AnnouncementCreate`/`AnnouncementUpdate` forbid unknown fields?** `RegisterRequest`
   already uses `ConfigDict(extra="forbid")` for exactly this reason (a client must not supply
   ownership/privilege fields). For announcements, extras are *ignored* instead. My recommendation:
   `extra="forbid"` on `AnnouncementCreate` (there is no current client that sends extras — the
   frontend only lists, creates and deletes), and leave `AnnouncementUpdate` permissive so a client
   can round-trip a fetched object without a 422. Note that no client PATCHes announcements today;
   the frontend does not use PATCH at all.
4. **`AnnouncementRepository.get_by_id` (unscoped) has no callers** but is retained. The security
   skill asks for unscoped getters to be flagged; this one is **not** reachable from any route, so it
   is a minor hazard rather than a defect. Keep or delete?
5. **Model/migration FK naming drift.** The model declares `ForeignKey("estates.estate_id", ...)` and
   `ForeignKey("users.user_id", ...)` **without names**, while the migration names the estate FK
   `fk_announcements_estate_id_estates`. Every other estate-scoped model in this tree names its FK
   (for example `AICallEvent`). If `alembic revision --autogenerate` is ever run, unnamed FKs are the
   kind of difference that produces spurious constraint churn. Not changed here (it would mean
   editing the model for cosmetics) — worth a cleanup batch.
6. **Announcements have no audit trail for who changed what.** `updated_at` moves but the previous
   value is lost, so an HOA edit is untraceable. Related to the DELETE question; also deferred.
7. Unchanged from earlier sessions: root-level `CLAUDE_README.md`, `ARCHITECTURE_AND_DOMAIN.md` and
   `DEVELOPMENT_AND_VALIDATION.md` still do not exist, and `docs/PROJECT_STATUS.md` still overstates
   the analytics entity inventory (noted in `docs/progress/score-authority.md`).
