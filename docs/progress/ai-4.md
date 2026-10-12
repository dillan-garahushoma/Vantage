# BATCH AI-4 — STOPPED: prerequisite (Task 7) is missing in this tree

> **Update 2026-10-11:** Task 7 is now in the tree (7A/7B/7C), so AI-4 was re-issued
> and **implemented**. The completion report is the "Session 2" section at the end
> of this file. The stop report below is kept unchanged as the record of why the
> batch stopped the first time, and its open questions are now answered there.

Session: 2026-10-10. Branch `valora-work`. **No application code was written and no migration was
added.** This note is the only file created.

The batch opens with an explicit gate:

> BATCH AI-4. PREREQUISITE: Task 7 passed (snapshot model, calculation, history API). Verify in the
> tree; if missing, stop. Use the snapshot's REAL field names.

Task 7 is **not** in this tree, so I stopped. Implementing `brief_facts.py` would require inventing the
snapshot's field names, which the same sentence forbids, and every later item in the batch (the
migration's `snapshot_id` FK, the template brief, the "latest snapshot" service, the 404-when-no-snapshot
behaviour) hangs off that model. There is no correct small version of this batch to do first.

## Evidence that the prerequisite is absent

| Check (run from `backend/`) | Result |
| --- | --- |
| `grep -rni "snapshot" app alembic tests` | **no matches** (the only hit anywhere is a stale `alembic/versions/__pycache__/be47e164c220_initial_structure.cpython-314.pyc`, whose `.py` no longer exists after the consolidated migration) |
| `grep -rni "engine_version\|insufficient_data" app tests` | **no matches** — neither the versioned snapshot field nor the component flag exists |
| `grep -rni "incident" app alembic/versions tests --include=*.py` | **no matches** — see the second gap below |
| `ls app/analytics/{models,repositories,services,schemas}` | only `ai_analytic.py` (legacy property valuation), `ai_call_event.py`; `living_score_repository.py`, `living_score_service.py`, `living_score.py` |
| `cat app/analytics/api/router.py` | **one route**, `GET /analytics/status`, returning a static "scaffolded" dict |
| `grep -n "include_router" app/api/router.py` | the analytics router is mounted, but it contributes only `/status` |
| `grep -n "create_table\|score" alembic/versions/5c5c0e0ef686_consolidated_architecture.py` | tables are `login_attempts, properties, service_providers, users, ai_analytics, announcements, complaints, listings, reviews, sales, sessions, maintenance_work_orders` — **no snapshot / living-score table**; `ai_analytics` is the legacy valuation model |
| `grep -rni "task 7" docs tasks` | `tasks/todo.md` **Task 7: Implement Living Score v1.0.0 and immutable history** — all three acceptance criteria are unticked `[ ]`; Task 6 is unticked too |
| `git branch -a`, `git stash list`, `git log --oneline -6` | Task 7 is not parked on another branch (branches are `main`, `valora-work`, five `agents/*`, `codex/valora-core-foundation`, `feature/kimi-agent`) and nothing is stashed. Head is `0849c05 feat: complete Phase 1 Batch A API contract` |

What *does* exist is the **legacy** per-property score: `LegacyPropertyScoreService` /
`LegacyPropertyScoreRepository` / `LegacyPropertyScoreResponse` — a 40/30/30 community/maintenance/provider
blend over a single `unit_id`, computed on the fly, never persisted, with no `estate_id` and no
`engine_version`. It is not the estate snapshot engine Task 7 asks for, and it is wired to the property
route, not to analytics.

## Second gap: the facts AI-4 needs from Task 6 are also absent

`BriefFacts` must carry an `incidents` count. There is no security-incident model, table or service
anywhere in the tree (the grep above is empty). Announcements do exist (`app/community/models/announcement.py`,
scoped to the estate by `e5b8c2f1a4d7`), so the rest of the complaint/work-order inputs for the facts
object would be available — but the incidents component could only ever be shipped as a permanent
`insufficient_data`, which is a product decision I am not making on my own authority.

## Upstream decision that gated this batch — **resolved 2026-10-10, after the stop**

> Recorded at the time of the stop as an open conflict. It was settled afterwards by
> product-owner decision: the five-component estate-level `v1.0.0` score is
> authoritative (see `docs/ADR-005-Living-Score-Authority.md` and
> `docs/progress/score-authority.md`). The analysis below is left as the record of what
> the blocker was; the resolution did not build anything, so the prerequisite gap this
> batch stopped on is still open.

`docs/progress/group8-vantage-reconciliation.md` §8.1 records a **Living Score authority conflict** that
is still open:

- the tree's legacy implementation is **40/30/30** (community / maintenance / provider);
- `.agents/skills/valora-living-score/SKILL.md` specifies a **five-component** engine with weights
  `0.30 resolution / 0.25 frequency / 0.20 security / 0.15 satisfaction / 0.10 infrastructure`, a 90-day
  window, `LivingScoreSnapshot`, and `engine_version` (`v1.0.0`);
- the reconciliation report says the five-component formula **must not be implemented** until the product
  owner confirms which authority governs.

`BriefFacts` is defined component-by-component (each component's `score`, `weight`,
`insufficient_data`), so AI-4 cannot be written correctly until that decision is made. This is not an
implementation detail I could paper over: the two models have different component sets and different
weights, and the deterministic template brief would bake the choice into a persistent, immutable row.

## Commands run and results, exactly as observed

From `backend/`, interpreter `backend\venv\Scripts\python.exe`:

| Command | Result |
| --- | --- |
| `-m pytest tests -q` (baseline, with `set -o pipefail`) | **290 passed, 2 skipped, 4 warnings in 83.56s** — exit 0. The tree is green and unchanged by this session. |
| `-m alembic -c alembic.ini heads` (with `DATABASE_URL` / `SECRET_KEY` exported from `backend/.env.example` values) | `b8e5f2d1c3a4 (head)` — single head, unchanged |
| `-m alembic -c alembic.ini history` | `5c5c0e0ef686 → 103dd39ca30e → … → b8e5f2d1c3a4 (head)`, single lineage |

The 2 skips are the integration tests that require `TEST_DATABASE_URL`, which is unset in this terminal.
They are **not** counted as passes. No database was touched, no migration was applied, no provider was
contacted, and no key was read, printed or logged.

## Files changed

| File | Change |
| --- | --- |
| `docs/progress/ai-4.md` | **new** — this stop report |

No other file was created, edited or deleted. Nothing was staged, committed, reset or stashed; the
pre-existing dirty working tree (Phase 1 / AI-1..AI-3 / PILOT-1 work) was left exactly as found.

## Recommended next step

1. **Task 7 first**, as its own batch: resolve the §8.1 formula authority, then build the snapshot model,
   the 90-day calculation and the history API. That batch is what AI-4's gate refers to.
2. **Task 6 incidents** (or an explicit decision to ship `insufficient_data` for that component), because
   `BriefFacts.incidents` has no source without it.
3. Then re-issue AI-4 unchanged; nothing in it needs redesign.

If the intent is instead to get *something* AI-shaped in front of the pilot before Task 7, the honest
alternative is to re-scope: a template-only brief (item 4's deterministic path) over the *legacy* 40/30/30
per-property score. That still needs a persisted, versioned snapshot table — so it is most of Task 7 —
and it would contradict §8.1. I did not do it.

## Open questions

1. **Which Living Score authority governs?** — **RESOLVED 2026-10-10**, after this stop:
   the five-component estate-level `v1.0.0` score
   (`docs/ADR-005-Living-Score-Authority.md`, and §8.1 of
   `docs/progress/group8-vantage-reconciliation.md`). The legacy 40/30/30 code is not
   Living Score v1. AI-4 is now blocked only by the missing Task 7 implementation, not
   by this product question.
2. **Does `incidents` ship as `insufficient_data` until Task 6 exists**, or does AI-4 wait for Task 6?
3. **Where does the snapshot table live** (`analytics` module, as AI-4 assumes, or `community`)? AI-4
   specifies a `snapshot_id` FK to "the real snapshot table" without naming it, so the target module
   should be fixed in the Task 7 batch.
4. AGENTS.md still names root-level `CLAUDE_README.md`, `ARCHITECTURE_AND_DOMAIN.md`,
   `EXECUTION_ROADMAP.md` and `DEVELOPMENT_AND_VALIDATION.md`; the first two and the last do not exist
   anywhere (only `docs/EXECUTION_ROADMAP.md`). Unchanged from AI-1..AI-3 and PILOT-1; not fixed here.

---

# BATCH AI-4 — Estate Health Brief (Session 2, 2026-10-11) — IMPLEMENTED

**Scope:** one new AI sub-package, two repositories, two models, one additive
migration, one service, three endpoints, one runbook line. The legacy property
score was not touched. Nothing was committed.

## Prerequisites, verified in the tree before writing code

| Prerequisite | Reality in the tree |
| --- | --- |
| Snapshot model / repository / service (7B) | `LivingScoreSnapshot`, `LivingScoreSnapshotRepository`, **`LivingScoreService`** in `app/analytics/services/estate_living_score_service.py` -- the batch calls it `EstateLivingScoreService`, which does not exist. The real name was used. |
| 7C endpoints | `GET/POST /api/v1/analytics/living-score`, `GET .../history`, plus the three `LivingScore*` DTOs |
| `GuardedLLMClient` and `ai_call_events` (AI-2) | `app/core/ai/{client,guard,factory,fake,gemini,openai_compat,redaction,errors}.py`; `AICallEvent` + `AICallEventRepository` |
| `estates.is_demo` | `Estate.is_demo`, boolean, not null, server default false |
| Migration head | `c4d8f1a7b9e3` (`alembic heads`, single) |

## Done

| File | Contents |
| --- | --- |
| `backend/app/analytics/ai/brief_facts.py` | `BriefFacts`, `BriefOverall`, `BriefComponent`, `build_brief_facts(snapshot, previous_30d, previous_90d)`. Pure; numbers only; the two deltas are computed here. |
| `backend/app/analytics/ai/brief_output.py` | `PROMPT_VERSION="brief-v1"`, the system prompt, `build_user_prompt`, `brief_output_schema()`, `BriefOutput`/`BriefDriver`/`BriefAction`. |
| `backend/app/analytics/ai/grounding.py` | `GroundingViolation`, `allowed_values`, `numbers_in`, `validate_grounding`. |
| `backend/app/analytics/ai/template.py` | `build_template_brief(snapshot, facts)` -- rebuilt on demand, never stored. |
| `backend/app/analytics/domain/insight_vocabulary.py` | Kind and origin vocabularies, the 500-character comment bound, and the SQL check bodies the model and the migration share. |
| `backend/app/analytics/models/ai_insight.py`, `.../ai_insight_feedback.py` | The two new tables. |
| `backend/app/analytics/repositories/ai_insight_repository.py`, `.../ai_insight_feedback_repository.py` | Append-only; `add`, `get_for_snapshot`, `get_by_id_in_estate`, `get_by_insight_and_user`, plus pure statement builders. |
| `backend/app/analytics/repositories/living_score_snapshot_repository.py` | **Additive:** `latest_on_or_before` / `latest_on_or_before_statement` -- the read the comparison needs. Still no update, no delete. |
| `backend/alembic/versions/d9f2a4c7e1b3_add_ai_insights.py` | Additive `upgrade`, working `downgrade`, new head after `c4d8f1a7b9e3`. |
| `backend/app/analytics/services/health_brief_service.py` | `read`, `generate`, `feedback`, and every fallback path. |
| `backend/app/analytics/schemas/health_brief.py` | `HealthBriefResponse`, `HealthBriefFeedbackRequest` (`extra="forbid"`), `HealthBriefFeedbackResponse`. |
| `backend/app/analytics/api/health_brief.py` | The three thin routes; wired into `app/analytics/api/router.py`. |
| `backend/app/db/database.py` | Two lines: registers both models so `Base.metadata` is complete. |
| `docs/PILOT_RUNBOOK.md` | One line in section 4: the Health Brief sends the provider **aggregates only**. |
| `docs/openapi.json` | Regenerated with the existing `python -m app.cli export-openapi`. |

### Endpoints

| Method | Path | Who | Result |
| --- | --- | --- | --- |
| `GET` | `/api/v1/analytics/health-brief?estate_id=` | estate member | The stored AI brief, or the template (`source`, `ai_unavailable_reason`) |
| `POST` | `/api/v1/analytics/health-brief?estate_id=` | global `hoa_admin` **and** member | `200`: generates at most once per score, then returns the stored brief |
| `POST` | `/api/v1/analytics/health-brief/{insight_id}/feedback?estate_id=` | estate member | `200`; `409` on a repeat; `404` when the brief is another estate's |

### How the facts stay honest

`build_brief_facts` is a pure projection of stored rows. Every stored value is
coerced to `Decimal`/`int`; a string that is not a number raises, so the engine's
prose, a complaint description, a name or an injected instruction cannot ride into
a prompt. A test dumps the facts JSON and asserts the engine's benchmark,
explanation and recommendation markers are absent, and that every `inputs` value
is numeric.

The grounding validator then checks the other direction: every number in the
brief's text must equal a number in FACTS by absolute value at 0, 1 or 2 decimal
places (half up). "83.3" is accepted for 83.32; "1.13" is accepted for a delta of
-1.13; "77.40" and "0.25" for a 25.00 weight are refused. `score_min`/`score_max`
are part of FACTS so that "out of 100" is a supplied number rather than an implied
one.

## Tests added and passing

| Command (from `backend/`) | Result |
| --- | --- |
| `pytest tests/test_health_brief_facts.py -q` | **44 passed** (32 test functions, parametrised) |
| `pytest tests/test_health_brief_service.py -q` | **32 passed** |
| `pytest tests/test_health_brief_contract.py -q` | **31 passed** |
| `pytest tests -q` (no `TEST_DATABASE_URL`) | **608 passed, 63 skipped** |
| `pytest tests -q` (with `TEST_DATABASE_URL`) | **671 passed, 0 skipped** |
| `pytest tests/test_health_brief_api.py -q` (with the database) | **19 passed** |
| `python -m compileall -q app` | clean |
| `flake8 app tests --count --select=E9,F63,F7,F82` | **0** |
| `git diff --check` | clean |
| `python -m alembic -c alembic.ini heads` | `d9f2a4c7e1b3 (head)` -- single head |
| `alembic upgrade head --sql` | exit 0, 23 `CREATE TABLE` (21 before + the 2 new) |
| `alembic downgrade head:c4d8f1a7b9e3 --sql` | exit 0, drops both new tables |

All the batch's named cases are covered. The behavioural ones live in
`test_health_brief_service.py` (in-memory fakes around the real `GatedLLMClient` +
`GuardedLLMClient`): insufficient data and AI-off are zero-provider-call paths; a
provider error, an exhausted budget, non-object output, wrong-shaped output and
ungrounded output each return 200 with the right reason, store no brief, and leave
a later attempt working; feedback is once per member with a 404 for another
estate's brief. The DB-backed file proves the tenant boundary and the real
constraints: member reads, 404 with no snapshot, resident 403, cross-estate 403,
the unique constraint rejecting a duplicate brief and a duplicate verdict, the
comment check, and the nine named constraints existing in the migrated database.

### The migration was applied to a real database, not just rendered

The harness applied `d9f2a4c7e1b3` to the disposable `valora_test_batch7c`
database (already carrying the 7B/7C tables), which is what makes the constraint
assertions above real rather than text-matching. `valora_db` was never touched.

## Deviations and judgement calls

1. **`score_min` / `score_max` added to FACTS.** The batch lists the facts fields;
   these two are additive. Without them a model writing "83.32 out of 100" would
   be rejected for the number 100, which is the engine's documented bound rather
   than an invention. Adding them keeps the grounding rule literal instead of
   quietly exempting 0 and 100 inside the validator.
2. **`generated_at` is null for a template.** Nothing was generated and nothing was
   stored, so there is no generation event to name. An AI brief reports its row's
   `created_at`.
3. **`ai_unavailable_reason="insufficient_data"` when the score itself is not
   measurable.** AI was not attempted and did not fail; the field is read as "why
   is there no AI brief?", and a UI needs the distinction between "not enough of
   the estate is measurable yet" and "the provider is down".
4. **The failure path commits once.** The guard flushes an audit row into
   `ai_call_events` before raising (a rejection, a timeout, a provider failure).
   Returning the template without committing would roll that row away and make
   exactly the failures worth auditing invisible, contradicting ADR-004. So a
   failed generate commits only that row -- which is why those tests assert
   `commits == 1` and `insights.added == []`.
5. **A `provider_failed`/`ok` ledger row can still end in a template.** `GuardedLLMClient`
   records provider-level success; the schema and grounding checks happen after it,
   in this service. A row with status `ok` therefore does not guarantee a stored
   brief. Recorded as a limitation, not fixed here (changing it means changing AI-2's
   contract).
6. **A lost loser.** If two generates race, the loser's ledger row is rolled back
   with its transaction, so that attempt is not counted against the budget. Rare,
   and the direction that matters for cost (the winner's row) is preserved.
7. **The fake provider stores "fake" text.** `FakeLLMClient` synthesises
   schema-shaped strings, so `AI_PROVIDER=fake` produces a valid, grounded but
   meaningless brief. That is correct for a development-only adapter, and it is why
   the runbook says not to pilot on the fake provider.
8. **A 7B guard was updated.** `test_snapshot_repository_is_append_only` pinned the
   repository's exact public surface; the new read-only `latest_on_or_before` pair
   was added to that set, with a comment. The append-only assertions are untouched.

## A testing defect found and fixed (worth reading)

`backend/.env` on this workstation has **`AI_ENABLED=true`, `AI_INSIGHTS_ENABLED=true`,
`AI_PROVIDER=gemini`** with a model configured. The first version of the integration
test "generate with AI off" therefore made a **live, real provider call** and failed
with `invalid_output` -- the provider answered, and its answer did not match the
contract. Two consequences:

* the test was wrong, not the code: it asserted AI-off behaviour while inheriting an
  AI-on environment. It now pins the environment (`monkeypatch.setenv` +
  `get_settings.cache_clear()`), so this file can never contact a provider; and
* it is worth knowing that **any** test which insists on AI-off must pin the
  environment first, because the developer's `.env` is read by `Settings`.

The file now also has a hermetic positive test: `AI_PROVIDER=fake` is switched on
explicitly, and the full path is asserted end to end against the database -- one
stored brief, one ledger row with `feature=insights`, and a second generate that
returns the same `insight_id` while making no second provider attempt.

## Written but not run

- **A real provider brief** (Gemini or an OpenAI-compatible endpoint): deliberately
  not run. Aside from the accidental call described above, every AI path in this
  session was exercised with explicit settings or the fake adapter, with no network.
- Nothing else is unrun: the migration was applied to a disposable database, and
  both offline SQL directions were generated.

## Open questions

1. **What should the brief do with the four components that are not measured?**
   The template currently lists them by label ("Still limited data for: ..."). A
   product decision on wording would be better than mine.
2. **Should the ledger record validation and grounding failures distinctly?**
   Today only the provider's outcome is recorded (see deviation 5), so a brief that
   was rejected for an invented number looks like a success in `ai_call_events`.
   The honest fix is a new ledger status, which is an AI-2 change.
3. **Feedback on a template.** A template has no `insight_id`, so it cannot be
   rated. If residents should be able to say "this template is unhelpful", that
   needs a stored row, which contradicts "a template is never stored".
4. AGENTS.md still names four skills and three root documents that do not exist   (`valora-testing`, `valora-migration-safety`, `valora-security-review`,
   `valora-session-protocol`; `CLAUDE_README.md`, `ARCHITECTURE_AND_DOMAIN.md`,
   `DEVELOPMENT_AND_VALIDATION.md`). Of the skills this batch names, only
   `valora-living-score`, `valora-data-strategy` and `valora-api-contracts` exist.
   Unchanged from the previous sessions; not fixed here.

5. **The pilot report cannot see the brief tables.** `scripts/ai_pilot_report.py`
   probes `health_briefs` / `health_brief_feedback`, which are not the names this
   batch was told to use (`ai_insights` / `ai_insight_feedback`), so it still
   reports them as absent. See the gap recorded under the final verification pass
   below.

### Final verification pass (re-run after the dead-code cleanup)

A small cleanup (an unused import in the service, unused scaffolding in two of the
new test files) landed *after* the numbers above were first recorded, so every
gate was re-run against the final files. The counts did not move:

| Command (from `backend/`) | Result |
| --- | --- |
| `pytest tests -q` (no `TEST_DATABASE_URL`) | **608 passed, 63 skipped** (exit 0) |
| `pytest tests -q` (with `TEST_DATABASE_URL`) | **671 passed, 0 skipped** (exit 0) |
| `pytest tests/test_health_brief_facts.py tests/test_health_brief_service.py tests/test_health_brief_contract.py -q` | **107 passed** |
| `pytest tests/test_health_brief_api.py -q` (with the database) | **19 passed** (107 + 19 = 126, the four new files together) |
| `python -m compileall -q app` | clean |
| `flake8 app tests --count --select=E9,F63,F7,F82` | **0** |
| `python -m alembic -c alembic.ini heads` | `d9f2a4c7e1b3 (head)` -- single head |
| `alembic upgrade head --sql` | exit 0, **23 `CREATE TABLE`**, 15 lines naming the two new tables |
| `alembic downgrade head:c4d8f1a7b9e3 --sql` | exit 0, `DROP TABLE ai_insight_feedback` then `ai_insights` |
| `python -m app.cli export-openapi` | exit 0; `docs/openapi.json` **byte-identical** to the committed-in-tree copy, so it is current |
| `git diff --check` | clean |

The logger in `health_brief_service.py` was re-read and kept: all three call sites
log only the estate id and a closed reason code (`exc.reason`, `exc.code`,
`INVALID_REASON`), never a prompt, an output or any estate content.

### Gap found while re-verifying: the pilot report still calls the brief tables absent

`scripts/ai_pilot_report.py` (AI-3) probes a fixed tuple,
`BRIEF_TABLES = ("health_briefs", "health_brief_feedback")`, and its test seeds
`ALL_TABLES = ("ai_call_events", "complaint_ai_suggestions")`. The batch named the
real tables `ai_insights` and `ai_insight_feedback`, so on a database that has this
migration the report's probe still finds nothing and prints
*"not available yet: the Health Brief tables ... arrive in BATCH AI-4"* -- now a
false statement. The script is AI-3's and the batch does not ask for it, so it was
**not** changed (the alternative was editing AI-3's script and its pinned test away
from this batch's scope). Recorded as remaining work and open question 5 above.

The one clause this makes stale *in the runbook I was asked to edit* was corrected:
section 5 no longer says the Health Brief section is missing "until AI-4 defines
those tables"; it now states the tables exist as `ai_insights` /
`ai_insight_feedback` and that the report's probe names do not match them yet.

## Remaining work (not done in this batch)

1. Point `scripts/ai_pilot_report.py` at `ai_insights` / `ai_insight_feedback` (or
extend `BRIEF_TABLES`) and update its test, so the pilot report stops claiming the
tables are missing. AI-3's scope.
2. Consider recording validation/grounding rejections distinctly in `ai_call_events`
(open question 2).
3. Product decision on the template's insufficient-data wording (open question 1).
