# VERIFY-1 — Database-backed run, failure classification and migration cycle

Batch: VERIFY-1. Status: **complete**. The suite is green against a throwaway
PostgreSQL. No production code was changed; every fix is in test code. No
`(c)` real-production-bug failures were found.

**Throwaway target (printed before use):**
`valora_verify_test_2026_10_11` inside the local Docker container `valora_db`
(`localhost:5432`). It was created empty at the start of this session and
**dropped at the end**.

> Deviation: the batch named the database `valora_verify_<today>`
> (`valora_verify_2026_10_11`). `tests/conftest.py` refuses to run integration
> tests unless the `TEST_DATABASE_URL` database name contains `test`
> (data-truncation guard). The name was therefore `valora_verify_test_2026_10_11`
> so both the batch intent and the guard are satisfied. The dev/pilot databases
> (`valora_db`, `valora_pilot_dev`, `valora_ai5_wiring`) were never used.

> Skill note: `valora-testing` and `valora-security-review` are not present in
> this checkout (`.agents/skills/` holds only api-contracts, architecture,
> data-strategy, domain-model, living-score, product-design, quality-gates).
> `valora-quality-gates` was read instead.

## 1. Full suite with `TEST_DATABASE_URL`

The suite was run three times as fixes landed. Counts (pytest `-q`):

| Run | State | Result |
|---|---|---|
| #1 | TEST_DATABASE_URL set, **before** any fix | **644 passed, 6 failed, 75 errors** |
| #2 | after the `conftest.py` URL fix | **704 passed, 20 failed, 1 error** |
| #3 | after all test-code fixes | **725 passed, 0 failed, 0 skipped, 0 errors** (exit 0, 396s) |

**Skips:** 0 in run #3. Every integration test ran against the database; no skip
needed a reason because none occurred. (Without `TEST_DATABASE_URL`, the 78
`@pytest.mark.integration` tests auto-skip, as designed.)

## 2. Failure classification (every failure, with proof)

### (a) Test-helper defects — fixed in test code

1. **`conftest.py` migrated the wrong database (75 errors).**
   `apply_migrations` set the URL on the Alembic `Config`, but
   `alembic/env.py` overwrites `sqlalchemy.url` with `settings.DATABASE_URL`.
   Under tests that resolved to `test:test@localhost:5432/valora_test` (no `test`
   role), so every integration fixture setup raised
   `ConnectionResetError [WinError 64]`.
   *Fix:* point the app's `DATABASE_URL` env var at `TEST_DATABASE_URL` at conftest
   import time (before `Settings` is imported).

2. **Reserved-domain emails in ONB-1 integration tests (14 failures).**
   Registering with `onb_*@valora.test` returned `422`: `email-validator` rejects
   special-use TLDs (`.test`, `.example`, `.invalid`). The unit tests already used
   `@example.com` and passed.
   *Fix:* changed the test emails to `@example.com`.

3. **`httpx` `get()` called with a JSON body (6 failures).**
   The cross-estate sweep called `async_client.get(url, json=body, ...)` →
   `TypeError: AsyncClient.get() got an unexpected keyword argument 'json'`.
   *Fix:* send a body only for the `post` variants.

The `tests/factories.py` `hoa_approved` mismatch flagged by the batch **no longer
exists** — the file already sets `user.hoa_approved = True` after creation and
commits once (comment present at `factories.py`). No change was needed.

### (b) Depends on the current date/time or test order — fixed in test code where deterministic

4. **`test_ai_guard.py` ×4 (budget cap, provider failures, estate isolation,
   24h window).** Root cause proven: the fake ledger stamps rows with a frozen
   clock `T0 = 2026-10-10 12:00`, but `make_guard` passed `clock=None`, so
   `GuardedLLMClient` used the **real** `datetime.now(timezone.utc)`. Its 24h
   window (`now - 24h`) drifted past the stored `T0` rows, so `count_since`
   returned 0, the cap never bound, and `AIUnavailableError` was not raised
   ("DID NOT RAISE"). Green in AI-2 on 2026-10-10; red on 2026-10-11.
   *Fix:* `make_guard` now defaults the guard clock to the same frozen `T0`.
   This is **not** a production bug: in production the ledger and the guard both
   read the real clock, so they agree; only the test injected one clock.

5. **`test_ai_pilot_report.py::test_the_days_window_is_a_bound_parameter` (1).**
   Root cause proven: `NOW` was hardcoded to `2026-10-10 12:00` while the report
   reads the real clock; the assertion allows only one day of slack, so it failed
   once real time drifted a day.
   *Fix:* `NOW = datetime.now(timezone.utc)` captured at import.

6. **`test_announcements_estate_scoping.py::test_member_of_estate_a_cannot_list_estate_b_announcements`
   and an error in `test_living_score_api.py::test_a_member_can_read_the_latest_score`
   (run #2 only).** Both are `WinError 64` TCP resets on the client→Postgres
   connection during an HTTP request. Proof they are order/load-dependent:
   **each passes alone**, they failed only inside the full run, and **neither
   recurred** in the clean run #3. Postgres logged no connection error; the reset
   is on the Windows/Docker transport under sustained open/close churn.
   *No deterministic test-code fix applied* — the failure is a transient Docker
   Desktop networking reset, and shrinking the connection churn would require
   session-scoped engines + session-scoped event loops (a large config change the
   batch asks to avoid). Suggested mitigation for a future batch: add
   `asyncio_default_test_loop_scope = session` and a session-scoped engine.

### (c) Real production bugs

**None.** The AI cost-cap tests were treated as real until proven otherwise; they
were proven to be a frozen-clock test defect (see #4), and the guard's real-clock
behaviour is correct.

### git history caveat

`git log` in this working tree has only three commits (HEAD `0849c05`) and
`test_ai_guard.py` / `test_ai_pilot_report.py` are **untracked** (`??`), so
`git log`/`git blame` cannot attribute them. The baseline used instead is the
AI-2 and PILOT-1 progress reports (`docs/progress/ai-2.md`, `pilot-1.md`, dated
2026-10-10), which record those tests green, plus the hardcoded 2026-10-10
timestamps as direct proof.

## 3. ONB-1 database-backed tests (batch item 6)

`pytest tests/test_onb1_role_scoped_signup.py -m integration` → **15 passed, 33
deselected**. All 15 ran against the throwaway database and passed:

- **One-transaction signup with rollback on a duplicate estate name:**
  `test_estate_admin_signup_creates_estate_and_membership_then_lists_it`;
  `test_duplicate_estate_name_rolls_back_the_whole_signup` (asserts the rejected
  attempt leaves **no** orphan user and the first estate survives).
- **Cross-estate sweep:** `test_new_estate_admin_gets_403_or_404_on_another_estate`
  (10 parametrised cases — GET/POST on complaints, stats, announcements,
  incidents, properties, work-orders) — all return 403/404 for a fresh estate
  admin against a foreign estate.
- **Zero estate access for a provider:** `test_provider_signup_links_a_profile_and_grants_zero_estate_access`.
- **`platform_admin` unobtainable publicly:** `test_platform_admin_cannot_be_obtained_through_any_public_endpoint`.
- **Log redaction:** `test_a_password_never_appears_in_the_logs`.

The full file (unit + integration) also passes: **48 passed**.

## 4. Migration cycle on the throwaway database (batch item 7)

`alembic -c alembic.ini` with `DATABASE_URL` = the throwaway:

| Step | Result |
|---|---|
| `current` | `d9f2a4c7e1b3 (head)` |
| `downgrade base` | ran base downgrades; **0 non-`alembic_version` tables** remained |
| `upgrade head` (empty → head) | all revisions applied, ending `d9f2a4c7e1b3` |
| `downgrade -1` | `d9f2a4c7e1b3 -> c4d8f1a7b9e3` |
| `upgrade head` | `c4d8f1a7b9e3 -> d9f2a4c7e1b3` |
| `current` (final) | `d9f2a4c7e1b3 (head)` |

## 5. Files changed (test code only)

- `backend/tests/conftest.py` — point `DATABASE_URL` at `TEST_DATABASE_URL`.
- `backend/tests/test_ai_guard.py` — default the guard clock to the ledger's frozen `T0`.
- `backend/tests/test_ai_pilot_report.py` — `NOW` is captured at import, not hardcoded.
- `backend/tests/test_onb1_role_scoped_signup.py` — valid email domain; `get()` without a JSON body.

`backend/app/seed_demo.py` was **not touched**. No production code changed. No
`git commit`/`reset`/`checkout`/`stash` was run.

## 6. Commands run (exact)

| Command | Result |
|---|---|
| `docker exec valora_db psql -U valora_user -d postgres -c "CREATE DATABASE valora_verify_test_2026_10_11;"` | created |
| `TEST_DATABASE_URL=...ver_verify_test_2026_10_11 pytest tests -q` (run #1) | 644 passed, 6 failed, 75 errors |
| same (run #2) | 704 passed, 20 failed, 1 error |
| same (run #3) | **725 passed, 0 failed, 0 skipped** |
| `pytest tests/test_onb1_role_scoped_signup.py -m integration -q` | 15 passed, 33 deselected |
| `pytest tests/test_onb1_role_scoped_signup.py -q` | 48 passed |
| `pytest tests/test_ai_guard.py tests/test_ai_pilot_report.py -q` | 34 passed |
| `alembic -c alembic.ini downgrade base / upgrade head / downgrade -1 / upgrade head` | see §4 |
| `python -m compileall -q app tests` | OK |
| `flake8 tests/conftest.py tests/test_ai_guard.py tests/test_ai_pilot_report.py tests/test_onb1_role_scoped_signup.py --select=E9,F63,F7,F82` | 0 |
| `git diff --check` | clean |
| `docker exec valora_db psql ... -c "DROP DATABASE valora_verify_test_2026_10_11;"` | dropped (see §7) |

## 7. Cleanup

The throwaway database `valora_verify_test_2026_10_11` was dropped at the end of
the session. The dev, demo and pilot databases were never touched.
