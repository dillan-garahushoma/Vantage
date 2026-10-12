# BATCH BE-1 — Publish the fixed vocabularies in the OpenAPI contract

Session: 2026-10-11. Branch `valora-work`. Status: **done**. No migration, no frontend change, no
seed-script edit, nothing committed, nothing reset.

AI-5 stopped because `TriageDecisionRequest.category/priority/trade` were plain strings in the
contract and the frontend's hand-copied lists had already drifted. This batch publishes the
vocabulary, so a client reads the allowed values instead of retyping them.

## What was done

**1. The vocabulary module owns the API aliases (single source, nothing retyped).**
`backend/app/community/domain/triage_vocabulary.py` already held the tuples; it now also holds the
four aliases built from them, so the triage DTOs and complaint creation share one definition:

```python
Category = Literal[*CATEGORIES]
Priority = Literal[*PRIORITIES]
Trade = Literal[*TRADES]
Decision = Literal[*DECISIONS]
```

This follows the in-repo precedent (`security_incident.py` derives `IncidentCategory = Literal[*CATEGORIES]`)
but places the aliases once in the vocabulary module instead of once per schema module, because two
schema modules now need them. FastAPI publishes a multi-value `Literal` as an inline `enum` array.

**2. Triage DTOs typed** (`backend/app/community/schemas/complaint_ai.py`):
`TriageDecisionRequest.category/priority/trade` are now `Category | None` / `Priority | None` /
`Trade | None` — still nullable, still defaulting to `None`. The three hand-written `field_validator`s
were removed: they were redundant with the type and their only job was repeating the tuples.
`TriageSuggestionResponse` gained types on the six label fields (`suggested_*` non-null as today,
`decided_*` nullable as today). This is safe for stored rows because the suggestion table's check
constraints already restrict those columns to the same tuples; there is no legacy free text there.
`TriageDecisionRequest.decision` is now `Decision` (derived from `DECISIONS`) — see deviations.

**3. Complaint creation typed** (`backend/app/community/schemas/complaint.py`):
`ComplaintCreate.category: Category` (was `str` with `min_length/max_length`) and
`ComplaintCreate.priority: Priority = "normal"` (was `str` with the hand-retyped regex
`^(low|normal|high|urgent)$`). `ComplaintResponse.category/priority` were **left as plain `str`**, as
the batch requires, so a row filed before the vocabulary existed still reads back.

**4. Contract regenerated** with the existing command — `python -m app.cli export-openapi` — and
verified deterministic (two consecutive exports, identical SHA-1).

What the contract publishes now (read out of `docs/openapi.json`):

```
ComplaintCreate.category            enum [water, electrical, security, noise, infrastructure,
                                          gardens, waste, parking, administrative, other]
ComplaintCreate.priority            enum [low, normal, high, urgent], default normal
TriageDecisionRequest.category      anyOf[ enum[...10 categories...], null ]
TriageDecisionRequest.priority      anyOf[ enum[low, normal, high, urgent], null ]
TriageDecisionRequest.trade         anyOf[ enum[plumber, electrician, security, landscaping,
                                          general_maintenance, pest_control, roofing, other], null ]
TriageDecisionRequest.decision      enum [accepted, overridden, dismissed]
TriageSuggestionResponse.suggested_category / .suggested_priority / .suggested_trade     enum (...)
TriageSuggestionResponse.decided_category   / .decided_priority   / .decided_trade       enum(...) | null
ComplaintResponse.category          {"type": "string"}   <-- unchanged, legacy rows still read
ComplaintResponse.priority          {"type": "string"}   <-- unchanged
```

## Tests added (failing first)

New file `backend/tests/test_vocabulary_openapi_contract.py` — 6 tests, all passing:

- `test_triage_decision_request_publishes_the_vocabulary` (category, priority, trade, decision)
- `test_triage_suggestion_response_publishes_the_vocabulary` (all six label fields)
- `test_complaint_create_publishes_the_vocabulary` (category, priority)
- `test_complaint_responses_stay_free_text_so_legacy_rows_still_read` (guards the decoupling)
- `test_complaint_create_rejects_values_outside_the_vocabulary` — HTTP 422, envelope
  `detail.code == "VALIDATION_ERROR"`, and the offending field named in `detail.details`
- `test_every_published_vocabulary_value_is_accepted_on_create` — every value the contract publishes
  is POSTed to `/api/v1/complaints` and answered `201` with the value echoed

Failing-first evidence (before the DTO change, `pytest tests/test_vocabulary_openapi_contract.py -q`):

```
AssertionError: no enum published for TriageDecisionRequest.category:
    {'anyOf': [{'type': 'string'}, {'type': 'null'}], 'title': 'Category'}
AssertionError: no enum published for TriageSuggestionResponse.suggested_category:
    {'type': 'string', 'title': 'Suggested Category'}
AssertionError: no enum published for ComplaintCreate.category:
    {'type': 'string', 'maxLength': 50, 'minLength': 2, 'title': 'Category'}
4 failed, 2 passed
```

Existing tests updated (no assertions weakened):

- `backend/tests/test_ai_triage_schema.py` — `test_priorities_match_the_existing_complaint_pattern`
  read `ComplaintCreate.model_fields["priority"].metadata[0].pattern`, the regex this batch deletes.
  Replaced by `test_complaint_priority_is_built_from_the_vocabulary`, which asserts the field's
  `Literal` args equal `PRIORITIES` (a stronger check than the old regex scan).
- `backend/tests/test_living_score_api.py` (2 fixtures) and `backend/tests/test_living_score_snapshots.py`
  (2 fixtures) — complaint rows were seeded with `category="plumbing"`; changed to `"water"`. The
  Living Score engine does not read `complaints.category` (verified by grep; the only `category`
  mention in `app/analytics/` is narrative copy), so no score changes.

## Callers that create complaints with other category strings

DTO-level callers already used vocabulary values, so none needed fixing:
`test_batch_b_authorization.py:112,120,129` (`ComplaintCreate(category="noise"|"water"|"parking")`).
`backend/scripts/provision_estate.py` and `backend/app/cli.py` never create complaints
(`provision_estate.py`'s `trade` strings are provider trades, a different vocabulary, and it is
untouched). No HTTP-level complaint POST in the suite used an off-vocabulary category.

**Seed script listed, not edited** — `backend/app/seed_demo.py` creates complaints with four
off-vocabulary categories (it writes rows directly, so nothing breaks today):

| line | value | in `CATEGORIES`? |
| --- | --- | --- |
| 191 | `plumbing` | no |
| 194 | `drainage` | no |
| 195 | `roads` | no |
| 196 | `garden` | no (`gardens` is) |

Its other three complaint categories — `security` (192), `electrical` (193), `noise` (197) — are
already vocabulary values.

## Commands run, with results exactly as observed

All from `backend/` unless noted; interpreter is `venv\Scripts\python.exe`.

| Command | Result |
| --- | --- |
| `pytest tests -q` — **before** any edit, no `TEST_DATABASE_URL` | **608 passed, 63 skipped** (84.12s), exit 0 |
| `pytest tests/test_vocabulary_openapi_contract.py -q` — before the fix | **4 failed, 2 passed**, exit 1 |
| `pytest tests/test_vocabulary_openapi_contract.py tests/test_ai_triage_schema.py tests/test_ai_triage_service.py -q` — after the fix | **82 passed**, exit 0 |
| `pytest tests -q` — after the fix, no `TEST_DATABASE_URL` | **614 passed, 63 skipped** (97.14s), exit 0 |
| `DATABASE_URL=...valora_test_be1 TEST_DATABASE_URL=...valora_test_be1 pytest tests -q` | **677 passed, 0 skipped, 0 failed** (350.73s), exit 0 |
| `TEST_DATABASE_URL=...valora_test_be1 pytest tests -q` (DATABASE_URL unset) | **615 passed, 62 errors** — see the harness note below |
| `DATABASE_URL=... SECRET_KEY=... python -m app.cli export-openapi` | exit 0, wrote `docs/openapi.json` |
| `sha1sum docs/openapi.json` before / after a second export | `155c863ad3ba5291625020148ae01aedb868bfc4` both times — deterministic |
| `DATABASE_URL=... SECRET_KEY=... python -m alembic -c alembic.ini heads` | `d9f2a4c7e1b3 (head)` — single head, **unchanged** (AI-4 recorded the same head) |
| `python -m compileall -q app` | exit 0 |
| `python -m flake8 app tests --count --select=E9,F63,F7,F82 --show-source --statistics` | `0`, exit 0 |
| `git diff --check` (repo root) | exit 0 |

**Integration run detail.** The 63 tests that skip without `TEST_DATABASE_URL` are the difference
between 614 and 677, so every integration test ran in the disposable-database run (no skips, no
failures). The database was my own `valora_test_be1` on the local PostgreSQL (created and dropped in
this session; `valora_db`, `valora_pilot_dev`, `valora_test` and `valora_test_batch7c` were never
written to).

**Harness note (pre-existing, not fixed here).** Setting only `TEST_DATABASE_URL` is not enough:
`alembic/env.py` overwrites the config URL with `settings.DATABASE_URL`, so conftest's
`set_main_option("sqlalchemy.url", ...)` from `TEST_DATABASE_URL` is discarded. With only
`TEST_DATABASE_URL` set, the `apply_migrations` fixture then tries the conftest default
`...//test:test@localhost:5432/valora_test` and all 62 DB-backed tests error at setup with
`asyncpg.exceptions.InvalidPasswordError: password authentication failed for user "test"`. Setting
`DATABASE_URL` to the same disposable test database as well makes the whole harness work. Not a
regression, and out of this batch's scope, but it is why the "with TEST_DATABASE_URL" run needs both
variables.

## Deviations, and things deliberately left alone

1. **`TriageDecisionRequest.decision` also derives from the vocabulary.** The batch names only
   category/priority/trade, but the file carried a hand-retyped `Literal["accepted","overridden","dismissed"]`
   that *is* `DECISIONS`. Deriving it changes no value and no contract byte; leaving a retyped copy in
   the one file this batch exists to de-copy seemed worse. Disclosed rather than hidden.
2. **Aliases live in the vocabulary module, not per-schema-module.** The incident precedent defines
   `IncidentCategory` inside `security_incident.py`; two schema modules need the triage values, so one
   definition in the source module avoids a second retyped alias.
3. **Response DTOs kept plain `str`** (`ComplaintResponse`, and `TriageSuggestionResponse.decision`),
   as instructed. The legacy free-text guarantee is now covered by a test.
4. **Fixtures that are not complaint creation keep their off-vocabulary values**: response DTO
   constructions like `ComplaintResponse(category="maintenance")`
   (`test_batch_a_pagination_contract.py:104`) and service-input fakes like
   `SimpleNamespace(category="plumbing")` (`test_batch_c_operational_flow.py:21`). Neither creates a
   complaint, and the first proves the response stays tolerant of legacy values.
5. **`seed_demo.py` was not touched** (listed above, as asked). No migration was added or edited; no
   file under `backend/alembic/` was modified by this session.
6. **No frontend change** was made. `frontend/src/lib/display.ts` still holds the drifted lists, which
   is now fixable from the contract.

## Written, not run

- `python -m alembic -c alembic.ini upgrade head --sql` (offline SQL) was **not** run — no migration
  is in scope for this batch, so there is nothing to render beyond what AI-4 already verified.
- Nothing else is written-but-not-run: every source and test change above was exercised by the suites
  listed.

## Open questions

1. **Python 3.10 vs `Literal[*TUPLE]`.** CI pins `python-version: '3.10'` and the Dockerfile uses
   `python:3.10-slim`, but starred expressions in subscripts are a Python 3.11 grammar change
   (PEP 646) — the same syntax `security_incident.py` already uses, so this batch adds no new class of
   problem, only more of it. I could not verify on 3.10 (no 3.10 interpreter on this machine; the venv
   is 3.14 and all runs above were 3.14). Bumping CI and the image to a 3.11+ interpreter is a
   separate decision and was not made here.
2. **`GET /api/v1/complaints?category=` is still a free string** (`max_length=50`). Filtering legacy
   free-text rows by an arbitrary string may be intended; if not, the filter is the next contract gap.
3. **`TriageSuggestionResponse.decision` is still `str | None`.** It is backed by a check constraint,
   so it could be typed for symmetry with the request; out of scope here.
4. **Who owns the UI vocabulary now?** The contract does, which is the point of this batch — but
   `display.ts` must actually be replaced by a contract read (AI-5's frontend work) for the drift to
   end.

## Files changed

| File | Change |
| --- | --- |
| `backend/app/community/domain/triage_vocabulary.py` | + `Category/Priority/Trade/Decision` `Literal` aliases built from the tuples |
| `backend/app/community/schemas/complaint_ai.py` | triage decision + suggestion label fields typed; three redundant validators removed |
| `backend/app/community/schemas/complaint.py` | `ComplaintCreate.category/priority` typed; hand-retyped priority regex removed |
| `backend/tests/test_vocabulary_openapi_contract.py` | **new** — 6 contract/vocabulary/422 tests |
| `backend/tests/test_ai_triage_schema.py` | pattern-based priority test replaced with a vocabulary-args test |
| `backend/tests/test_living_score_api.py` | 2 complaint fixtures: `plumbing` → `water` |
| `backend/tests/test_living_score_snapshots.py` | 2 complaint fixtures: `plumbing` → `water` |
| `docs/openapi.json` | regenerated with `python -m app.cli export-openapi` |

`docs/openapi.json` was already modified in the working tree by earlier sessions before this one; the
regeneration above is deterministic from the current code (verified by re-export).

## Recommended next step

Re-issue AI-5 unchanged: the triage override dropdowns can now read `category`, `priority` and `trade`
(and `decision`) from the schema, and `ComplaintCreate.category/priority` at the same time, so
`display.ts`'s stale lists can be deleted rather than extended.
