# BATCH AI-2 — demo flag, call ledger, budget guard, redaction, 503 mapping

Session: 2026-10-10. Branch `valora-work`. One additive migration, no endpoints, no
service callers. No commit was created.

Skills read before coding: `valora-migration-safety`, `valora-security-review`,
`valora-testing` (the three account skill files under `C:\Users\garah\Downloads\skills`),
plus `docs/ADR-002-AI-Assist-Layer.md` (now `ADR-004`) and `docs/progress/ai-1.md`.
`CLAUDE_README.md` and `ARCHITECTURE_AND_DOMAIN.md` still **do not exist in this tree**
(only `AGENTS.md` references them), exactly as reported in AI-1.

## Final status

Every batch item is implemented. All requested tests are written and passing; nothing
was left "written, not run" except the one thing the batch forbids running here (there
are no external credentials in this session, and this batch touches no provider).

## What is done, per batch item

1. **Migration `f6c9d3a8b2e1_add_ai_assist_ledger_and_demo_flag.py`** (`down_revision =
   e5b8c2f1a4d7`, the head found with `alembic heads`, not assumed):
   - `estates.is_demo BOOLEAN NOT NULL DEFAULT false` (backfills existing rows; no data is
     read, moved or deleted, so there is no pre-flight check that could fail).
   - `ai_call_events` with named constraints: `fk_ai_call_events_estate_id_estates`
     (ON DELETE RESTRICT), `ck_ai_call_events_status_allowed`
     (`ok, provider_failed, rejected_policy, rejected_budget`),
     `ix_ai_call_events_estate_id_created_at`.
   - **No content columns**: `event_id, estate_id, feature, provider, model, status,
     reason, latency_ms, input_chars, created_at`. A test asserts the exact column set and
     fails if any prompt/response/text-ish column is ever added.
   - Documented downgrade (drop index, drop table, drop column), verified in offline SQL.
   - Model registered in `app/db/database.py` and `Estate.is_demo` added to the ORM model.
2. **`AICallEventRepository`** (`app/analytics/repositories/`) — `record()` (flush only, no
   commit), `count_since()`, plus a pure `count_statement()` used by tests. Append-only: no
   update, delete, remove or save method, asserted by test. Every query filters
   `estate_id`.
3. **`GuardedLLMClient`** (`app/core/ai/guard.py`) — wraps an `LLMClient`, requires
   `estate_id` as a keyword (a call without it is a `TypeError`), counts the last 24h
   (`ok` + `provider_failed`) against `AI_DAILY_CALL_CAP_PER_ESTATE`, records
   `rejected_budget` and raises `AIUnavailableError("budget")` above the cap, and records
   `ok` / `provider_failed` with latency and input characters afterwards.
4. **`app/core/ai/redaction.py`** — pure `redact(text, *, known_names=(), unit_numbers=())`
   replacing `[EMAIL] [PHONE] [ID] [NAME] [UNIT]`, with the best-effort limits documented
   plainly in the module docstring.
5. **`error_handlers.ai_unavailable_exception_handler`** → HTTP 503, envelope code
   `AI_UNAVAILABLE`, generic message, `details.reason`, `X-Request-ID`; registered in
   `app/main.py`.
6. **`is_demo` on the existing estate read DTO** — `EstateAccessSummary`,
   `EstateAccessResponse` and the `GET /api/v1/auth/estates` mapping. The DTO already
   existed, so no new endpoint was created.

Also: `docs/ADR-002-AI-Assist-Layer.md` → **`docs/ADR-004-AI-Assist-Layer.md`**, with every
reference updated (`.env.example`, `app/core/config.py`, `docker-compose.yml`,
`docs/progress/ai-1.md`), and the ADR body updated to describe the ledger, the budget gate,
redaction, the 503 mapping and the failure policy it now really has.

## Tests added and passing

| File | Tests | What it pins |
| --- | --- | --- |
| `tests/test_ai_guard.py` | 13 | cap blocks call N+1 and records it; failures count toward the cap; policy rejections are free; disabled calls are not recorded; cross-estate isolation; 24h window; ok row is metadata-only; `estate_id` required; ledger write failure never breaks the caller; ledger read failure fails closed |
| `tests/test_ai_redaction.py` | 20 | SA phones (7 formats), 13-digit IDs incl. a leading-zero ID, emails, names (case-insensitive, whole word, 3+ char parts), unit numbers, mixed text, no-op text, regex metacharacters |
| `tests/test_ai_ledger_schema.py` | 13 | metadata-only columns, nullability, status check, named FK + index, `is_demo` default, append-only repository, estate-scoped compiled SQL, offline upgrade **and** downgrade SQL |
| `tests/test_ai_unavailable_http.py` | 9 | 503 envelope shape, every reason code, no key/prompt leak, handler registered |
| `tests/test_my_estates.py` (+1) | 1 | `is_demo` flows through the access summary |

## Verification — exact commands and results

Run from `backend/` with `venv\Scripts\python.exe`:

| Command | Result |
| --- | --- |
| `-m pytest tests/test_ai_guard.py tests/test_ai_redaction.py tests/test_ai_ledger_schema.py -q` (before implementing) | **exit 2** — `ModuleNotFoundError: No module named 'app.core.ai.guard'` / `...ai.redaction` / `app.analytics.models.ai_call_event`. The failing test came first. |
| `-m pytest tests/test_ai_guard.py tests/test_ai_redaction.py tests/test_my_estates.py -q` | 38 passed |
| `-m pytest tests/test_ai_ledger_schema.py tests/test_ai_unavailable_http.py -q` | 22 passed |
| `-m pytest tests -q` (with `pipefail`) | **168 passed, 2 skipped** (was 112 + 2 in AI-1) |
| `-m pytest tests -q -rs` | skips are explicit: `tests/test_harness_safety.py:5` and `tests/test_login_rate_limit.py:136`, both `TEST_DATABASE_URL is not set` |
| `-m compileall -q app scripts` | exit 0 |
| `-m alembic -c alembic.ini heads` | `f6c9d3a8b2e1 (head)` |
| `-m alembic -c alembic.ini upgrade head --sql` | exit 0; renders `ALTER TABLE estates ADD COLUMN is_demo BOOLEAN DEFAULT false NOT NULL`, `CREATE TABLE ai_call_events`, both named constraints, `CREATE INDEX ix_ai_call_events_estate_id_created_at` |
| `-m alembic -c alembic.ini downgrade head:e5b8c2f1a4d7 --sql` | exit 0; `DROP INDEX …`, `DROP TABLE ai_call_events`, `DROP COLUMN is_demo` (also asserted by test) |
| `-m flake8 app tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | 0 |
| `git diff --check` | exit 0 |

## Not run / not verified

- **No database was touched.** `TEST_DATABASE_URL` is not set in this session, so the two
  DB-backed integration tests **skipped** — I am not counting them as passes. That means
  the migration's online path (`upgrade head` against a real Postgres), the `is_demo`
  backfill against existing rows and every real ledger write are verified only as
  generated SQL and as code, not by execution.
- **No provider was contacted.** No API key exists in this session; the AI layer is
  entirely inert (nothing calls it).
- The `ai_call_events` table was never created on a live database, so the check constraint
  and FK are verified as compiled DDL, not as live database errors.

## Deviations and decisions worth knowing

1. **The budget gate fails closed, the ledger write is best-effort.** If the ledger count
   cannot be read, the guard refuses with `budget` rather than allowing an unmetered call
   — the safe direction for cost control, and still a clean `AIUnavailableError` so the
   product degrades. If a ledger *write* fails, the call still succeeds (the provider call
   is already paid for) but the failure is logged loudly, because a dropped row means the
   next count under-reports. Both directions are documented in the guard docstring and the
   ADR. I wrote the read-failure test as "does not block" first and inverted it when I
   settled the policy — flagged here rather than quietly.
2. **`disabled` outcomes are not recorded at all.** While the layer is off nothing was
   attempted and nothing was sent; logging every refused call would bury the real rows.
   `policy` rejections *are* recorded as `rejected_policy` (auditable, and they do not
   consume budget).
3. **The ledger lives in the analytics domain** (`app/analytics/models`,
   `app/analytics/repositories`), next to the existing `AIAnalytic` model, rather than in
   `app/core/ai`, which AI-1 established as DB-free infrastructure. `Guard` therefore
   depends on a `CallLedger` protocol and takes the repository by injection, so no
   ORM import leaks into `app/core/ai`.
4. **`is_demo` uses `getattr(estate, "is_demo", False)`** in the authorization service so
   the existing in-memory test fakes keep working.
5. Reason codes are unchanged and still closed; the 503 body carries only the reason code.
6. **Two names differ from the batch's shorthand**, both to match AI-1 and the existing
   codebase: the batch's `GuardedLLM` is `GuardedLLMClient` (siblings are `LLMClient` and
   `GatedLLMClient`), and the batch's `AIEventRepository` is `AICallEventRepository`,
   mirroring the model `AICallEvent` and the table `ai_call_events` it owns. No alias was
   added, so there is exactly one name for each thing. The interfaces themselves
   (`record()`, `count_since(estate_id, since, statuses)`, `generate_json(*, estate_id, …)`)
   are as specified.

## Open questions

1. **`backend/app/seed_demo.py` is untracked and not mine.** It creates the demo estate
   ("Highveld Ridge Estate") but never sets `is_demo=True`, so the flag has no producer
   yet. I did **not** edit another session's in-flight file. Someone should decide whether
   the seeder (or a later batch) marks demo estates.
2. **`docs/openapi.json` is stale and dirty.** It was already modified before this session
   and does not contain `is_demo` (nor `AI_UNAVAILABLE`, which is expected — exception
   handlers are not part of the OpenAPI document). I did not regenerate it to avoid
   clobbering another session's uncommitted changes: run
   `python -m app.cli export-openapi` once the tree is settled.
3. **No caller, so the guard is inert.** No service constructs `GuardedLLMClient` yet; the
   budget gate protects nothing until a feature uses it.
4. **No retention policy for `ai_call_events`.** Rows are small and metadata-only, but
   nothing prunes them. Worth deciding before a caller exists.
5. `AI_DAILY_CALL_CAP_PER_ESTATE` is per calendar-day only in the sense of a rolling 24h
   window; there is no per-minute burst limit. A tight loop would still burn the daily cap
   quickly.
