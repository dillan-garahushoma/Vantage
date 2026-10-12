# BATCH AI-3 — HOA triage suggestions (advisory only)

Session: 2026-10-10. Branch `valora-work`. One additive migration, three admin-only endpoints,
no commit created.

Skills read before coding: `valora-domain-model`, `valora-api-contracts`, `valora-architecture`
(from `.agents/skills/`), `valora-security-review`, `valora-migration-safety`, `valora-testing`
(the account skill files under `C:\Users\garah\Downloads\skills`), plus `docs/ADR-004-AI-Assist-Layer.md`
and `docs/progress/ai-1.md` / `ai-2.md`. `CLAUDE_README.md` and `ARCHITECTURE_AND_DOMAIN.md`
still **do not exist in this tree** (only `AGENTS.md` references them), as reported in AI-1 and AI-2.

Migration head before this batch: `f6c9d3a8b2e1` (found with `alembic heads`, not assumed).

## What is done, per batch item

1. **Vocabulary** — `app/community/domain/triage_vocabulary.py`: `CATEGORIES`, `PRIORITIES`
   (matching the existing `complaints.priority` pattern, asserted by test), `TRADES`, `DECISIONS`,
   `PROMPT_VERSION="triage-v1"`, membership helpers, `suggestion_schema()` and the `sql_in` /
   `nullable_sql_in` renderers. It is dependency-free and is the **single source** of the provider
   JSON schema, the API validators and the database check constraints, so the three cannot drift.
2. **Migration `b8e5f2d1c3a4`** (`down_revision = f6c9d3a8b2e1`) — `complaint_ai_suggestions`:
   `suggestion_id` PK, `complaint_id` UNIQUE FK `complaints` **CASCADE**, `estate_id` FK `estates`
   **RESTRICT**, suggested category/priority/trade, `provider`, `model`, `prompt_version`,
   `created_at`, then the write-once decision columns `decision`, `decided_by` FK `users` **SET
   NULL**, `decided_at`, `decided_category`, `decided_priority`, `decided_trade`; index
   `ix_complaint_ai_suggestions_estate_id_decision`; named `ck_` constraints for every vocabulary
   column, generated from the vocabulary tuples. **No content columns** (asserted by test). Model
   registered in `app/db/database.py`.
3. **Service** — `app/community/services/complaint_triage_service.py`.
   `generate(complaint_id, estate_id, admin)`, `get(...)`, `decide(complaint_id, estate_id, payload, admin)`.
   * `require_role(hoa_admin)` on every entry point: the global role **and** the estate membership.
   * Complaint loaded through the estate-scoped repository: another estate's complaint is a 404,
     never a 409 and never a provider call.
   * One suggestion per complaint: repeat `generate` returns the stored row with **no** LLM call.
   * Eligibility: anonymous → 409 (deliberate, see below); status must be `submitted`/`reviewed`.
   * Payload: `redact(category, description)` with the author's full name and the unit number as
     `known_names`/`unit_numbers`, plus the resident-chosen priority. Never a user id, name, unit
     number, estate name or timestamp.
   * Prompt: system prompt states the content is untrusted data and never instructions and that the
     model has no tools; the user message wraps the complaint in `<complaint>…</complaint>`.
   * Schema: `suggestion_schema()` — enums from the vocabulary only, `additionalProperties: false`.
   * Call: `GuardedLLMClient(..., feature="triage", data_class=personal)`; `AIUnavailableError`
     propagates to the AI-2 handler (503) and **no row is stored**, no commit happens.
   * Output: re-validated against the vocabulary before storing (untrusted provider output).
   * `decide`: write-once via a conditional `UPDATE … WHERE decision IS NULL`; `accepted` copies the
     suggestion, `overridden` records corrected labels (≥1 differs), `dismissed` records none.
4. **Endpoints** (`app/community/api/complaints.py`, `AdminOnly` + `estate_id` query, existing style):
   `POST /complaints/{id}/ai-suggestion`, `GET /complaints/{id}/ai-suggestion`,
   `POST /complaints/{id}/ai-suggestion/decision`.
5. **DTOs** — `app/community/schemas/complaint_ai.py`: `TriageSuggestionResponse` (suggestion,
   provider/model/prompt_version, decision fields) and `TriageDecisionRequest` (vocabulary-validated).
   No prompt field: asserted by test.
6. **ADR-004** updated: the layer is no longer inert, and the triage caller is documented as the
   reference implementation of "advisory only".

## Tests added and passing

| File | Tests | What it pins |
| --- | --- | --- |
| `tests/test_ai_triage_service.py` | 54 | admin-only (incl. the dual-role rule), cross-estate 404 with no provider call, anonymous 409, ineligible status 409, personal-data gate off → `policy` + no call + `rejected_policy` ledger row, master switch / feature flag off, provider failure → no row and no commit, payload privacy (no email/phone/ID/name/unit/timestamp/structural id), `<complaint>` wrapping, schema enums, prompt injection cannot change the schema or leave the enums, out-of-vocabulary + malformed output rejected with no row, null trade accepted, repeat generate = one LLM call, `get` never calls the provider, accept copies, override applies given fields only and rejects no-op/out-of-vocabulary, dismiss stores no labels,  write-once incl. the lost-race path, ledger rows with `feature="triage"`, and that generate/accept/override all leave the complaint row byte-identical |
| `tests/test_ai_triage_schema.py` | 22 | vocabulary exactness + no duplicates + priorities match the complaint pattern, schema built from the vocabulary and freshly built each call, table shape/nullability, no free-text columns, unique complaint, FK delete actions, check constraints, index columns, the conditional decision UPDATE is estate-scoped and write-once, offline upgrade + downgrade SQL, the three routes registered with the right methods,  response DTO has no prompt field, decision request vocabulary validation, and the AI client contract carries no tool parameter |

## Verification — exact commands and results

Run from `backend/` with `venv\Scripts\python.exe`:

| Command | Result |
| --- | --- |
| `-m pytest tests/test_ai_triage_service.py tests/test_ai_triage_schema.py -q` **before implementing** | **exit 2** — `ModuleNotFoundError: No module named 'app.community.domain.triage_vocabulary'`. The failing test came first. |
| same files, first full run after implementing | **2 failed, 70 passed** — both were bugs in my own test doubles (a settings helper that set `AI_PERSONAL_DATA_ALLOWED=True` while `AI_ENABLED=False`, which the config validator refuses; and a recording stub that could not express "the provider returned nothing"). Fixed the doubles, not the assertions. |
| `-m pytest tests/test_ai_triage_service.py -q` | 54 passed |
| `-m pytest tests/test_ai_triage_schema.py -q` | 22 passed |
| `-m pytest tests -q -rs` (with `pipefail`) | **244 passed, 2 skipped** (168 + 2 before this batch) |
| skips | explicit `TEST_DATABASE_URL is not set`: `tests/test_harness_safety.py:5`, `tests/test_login_rate_limit.py:136` |
| `-m compileall -q app scripts` | exit 0 |
| `-m alembic -c alembic.ini heads` | `b8e5f2d1c3a4 (head)` — exactly one head |
| `-m alembic -c alembic.ini upgrade head --sql` | exit 0; `complaint_ai_suggestions` appears 13 times (table, 7 named `ck_` constraints, unique, 3 FKs, index) |
| `-m alembic -c alembic.ini downgrade head:f6c9d3a8b2e1 --sql` | exit 0; drops the index and the table |
| `-m flake8 app tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | 0 |
| `git diff --check` | exit 0 |

## Not run / not verified

- **No database was touched.** `TEST_DATABASE_URL` is not set, so the two DB-backed integration tests
  skipped and **are not counted as passes**. The migration, the unique constraint, the check
  constraints, the FK delete actions, the conditional-UPDATE rowcount and real persistence are
  verified only as generated DDL, as compiled SQL and as code. The migration was **not applied**.
- **No provider was contacted.** Every test drives a recording stub through the real `GatedLLMClient`
  and `GuardedLLMClient`; `httpx.MockTransport` covers the adapters in AI-1. No key exists here.
- The end-to-end HTTP path (JWT → admin dependency → service → 503/200) is not exercised; the
  router contract is checked structurally against `app.openapi()` instead.

## Deviations and decisions worth knowing

1. **Anonymous complaints are refused with 409, as the batch requires.** This is a real product
   limitation, not just a guard: the author's name is what makes redaction work, so triaging an
   anonymous complaint would require holding the identity we are hiding. Flagged for the POPIA
   review the batch mentions.
2. **`accepted` with labels, or `dismissed` with labels, is a 409.** The batch does not say what to do
   with that combination; silently ignoring the extra labels would lose an admin's edit, so both are
   refused explicitly.
3. **An override applies only the fields the client sent** (`model_dump(exclude_unset=True)`):
   omitted fields fall back to the suggestion, and an explicit `"trade": null` clears the trade.
   Anything from the vocabulary is accepted by the DTO first (422), and "must differ from the
   suggestion" is the service's 409.
4. **The existing-suggestion lookup happens before the eligibility check**, so a repeat call is
   idempotent even after the complaint has moved on. It can only ever return a row this estate
   already had; it cannot create one.
5. **`GET` is admin-only too.** The batch only labelled generate and decide, but a suggestion is an
   internal HOA working aid and reading it with resident credentials would leak the AI's output.
6. **The write-once decision is a conditional UPDATE, not a read-then-write**, so two admins deciding
   concurrently yield exactly one decision; the loser gets 409. Only the statement shape is tested
   here (no database available) — the rowcount behaviour is unverified.
7. **Provider prose is not stored at all.** The output schema has only the three label fields and the
   `Mapping`/key-set check rejects anything extra, so no provider-authored text can reach the
   database, the API or a log line.
8. Naming: the table and service names follow the batch (`complaint_ai_suggestions`,
   `ComplaintTriageService`); the DTOs are `TriageSuggestionResponse` / `TriageDecisionRequest` to
   match the `*Response`/`*Request` convention of the complaints module.

## Open questions

1. **`estates.is_demo` is referenced by the batch but no rule in AI-3 needed it.** I did not invent a
   behaviour for it: gating AI on demo estates would either weaken the personal-data gate or turn a
   real estate's triage off for no stated reason. If the intent was "expose demo-ness to the client",
   the flag is already on the estate read DTO from AI-2 (`is_demo`); say the word and it can be added
   to the suggestion response as well.
2. **`docs/openapi.json` is stale and dirty** (another session's file, already modified before this
   batch, and it now lacks the three new paths). I did not regenerate it: run
   `python -m app.cli export-openapi` once the tree is settled.
3. **No review-queue endpoint.** `ComplaintAISuggestionRepository.list_for_estate()` exists for the
   HOA "undecided suggestions" queue but is not exposed; the batch only asked for the three
   per-complaint routes.
4. **No retention/pruning** for suggestions, and no metric for how often admins override rather than
   accept — which is the number that would tell us whether the suggestions are any good.
5. **`unit_id` remains a residual identifier on non-anonymous complaints** (noted by the security
   review skill for complaints generally). The AI payload never contains it, but the complaint row
   still links author and unit.
