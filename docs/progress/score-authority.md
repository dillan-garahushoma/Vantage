# Living Score authority — decision recorded

Session: 2026-10-10. Branch `valora-work`. **Documentation only: no code, no migration, no model,
no endpoint, no test, and no commit.** This note records a product-owner decision and where it was
written down.

## The decision

**The five-component, estate-level Living Score `v1.0.0` is authoritative.** Per
`.agents/skills/valora-living-score/SKILL.md`:

| Component | Weight |
| --- | --- |
| Resolution | 0.30 |
| Frequency | 0.25 |
| Security | 0.20 |
| Satisfaction | 0.15 |
| Infrastructure | 0.10 |

Rolling **90-day** window; every sub-score and the composite clamped to `[0, 100]`; strictly
deterministic and rule-based (no black-box or non-deterministic heuristic in the MVP); every
calculation persists an **immutable** `LivingScoreSnapshot` carrying `engine_version` (`v1.0.0`).

**The legacy 40/30/30 per-property score is not Living Score v1.** It stays exactly where ADR-003
put it — `LegacyPropertyScore*`, deprecated estate-authorized route, gated with the other legacy
surfaces — and must not be extended, re-weighted, presented to users as Living Score, blended into a
snapshot, or used to backfill one.

This agrees with `docs/SPEC-VALORA-MVP-CORE.md` line 17, which already recorded that the existing
property-only 40/30/30 score "has no rolling window or snapshots" and should be superseded by "the
documented estate-level five-component deterministic `v1.0.0` score".

## Where it was recorded

| File | Change |
| --- | --- |
| `docs/ADR-005-Living-Score-Authority.md` | **new** — the ADR, next number after ADR-004. Status, context (both candidate models), decision, consequences, verification and follow-ups. Structure and tone follow `ADR-003-legacy-isolation-and-provider-ratings.md`. |
| `docs/progress/group8-vantage-reconciliation.md` §8.1 | The finding is marked **RESOLVED 2026-10-10**, keeping the original text as the record of what the conflict was, followed by the resolution, the explicit "not Living Score v1" clause, and what the resolution does *not* do. |
| `docs/progress/group8-vantage-reconciliation.md` §9 and §10 | Cross-references updated so the document is no longer self-contradictory: the MVP-blocker bullet now says the decision is resolved and only the implementation remains; the "Recommended implementation sequence" item 1 is struck through and marked done, with the next step (Task 7) named. |
| `docs/PILOT_RUNBOOK.md` | ADR-005 added to the "Read this with" list, so an operator standing up the pilot does not mistake the deprecated legacy score route for Living Score. |
| `.agents/skills/valora-living-score/SKILL.md` | A short authority banner before the formula: this is the accepted definition; the legacy 40/30/30 score is not Living Score v1 and stays isolated; the engine described below is **not yet implemented**. |
| `docs/progress/ai-4.md` | The AI-4 stop report's open question #1 and its "unresolved upstream decision" heading are annotated as resolved, pointing at ADR-005 — otherwise that note would still tell a reader the question is open. |

## What was deliberately *not* done

- **No code.** No snapshot model, no `LivingScoreSnapshot` table, no 90-day calculation, no history
  API, no service, no endpoint, no route registration.
- **No migration.** `alembic heads` is unchanged; the head was not re-checked with a new revision
  because no revision file was added.
- **No test changes.** Nothing in `backend/tests/` was touched, so the suite is unaffected.
- **No commit, no push, no reset, no stash, no branch change.** Nothing was staged. The pre-existing
  dirty working tree was left exactly as found.
- **No change to the legacy score code.** `LegacyPropertyScoreService`, its repository, its response
  schema and its route are byte-identical. "Do not extend it" is a decision about future work, not an
  edit to today's code.
- **`tasks/todo.md` was not updated.** Task 7's checkboxes stay unticked until Task 7 is actually
  implemented; ticking them now would be a false claim. Not requested either.

## Consequences for the batches that were blocked

- **Task 7** is no longer blocked by a product question. It can be implemented as specified —
  five components, 90-day window, immutable versioned snapshots, history API — and remains the
  prerequisite for AI-4. It is still **not implemented**, so nothing downstream can proceed yet.
- **BATCH AI-4** remains stopped, for the original reason only: `BriefFacts` is defined from the
  snapshot's real field names, and the snapshot model does not exist. No redesign of AI-4 is needed.
- **The Security component has no input yet.** Security incidents are absent from the tree (Task 6
  unticked, zero matches for "incident" in `app`, `alembic/versions`, `tests`), so that sub-score can
  only read `insufficient_data` until an incident model exists. This is now a data-availability gap
  rather than a formula ambiguity, and the decision does not pretend otherwise.
- **The first `v1.0.0` snapshot begins the series.** There is no legitimate predecessor value, and
  none should be fabricated from the legacy score.

## Verification

Documentation-only change, so no test or build check applies to it. What was checked:

| Check | Result |
| --- | --- |
| `ls docs/*.md \| grep -i adr` | `ADR-001`, `ADR-002`, `ADR-003`, `ADR-004` present; **ADR-005 is the next free number** — no collision, and the earlier ADR-004/ADR-002 numbering collision was not repeated |
| `grep -rn "ADR-00" docs/*.md docs/progress/*.md AGENTS.md` | every pre-existing reference still resolves; the new one is `ADR-005-Living-Score-Authority.md` |
| `grep -rn "40/30/30\|five-component" docs/*.md docs/progress/*.md tasks/*.md` | the only remaining statements of the conflict are the annotated historical ones (`group8` §8.1, `ai-4.md`) plus the (correct) `SPEC-VALORA-MVP-CORE.md` line; no document still asserts the question is open |
| Line endings before editing | all LF (checked with `grep -c $'\r'`), so no file was rewritten with mixed endings |
| `git diff --check` | exit 0 |

Not run, deliberately: the pytest suite. No code or test file changed in this session, and the
AI-4 stop session immediately before it recorded **290 passed, 2 skipped** on this same tree with
no code change since. That figure is quoted from that session's output, not re-produced here; the
2 skips are the `TEST_DATABASE_URL` integration tests. No database was touched, no provider was
contacted, and no key, token or invitation code was read, printed or logged.

## Deviations from the instruction, and why

The instruction named §8.1 and "the ADR or notes following the existing numbering". I touched four
more places, each to stop a document from contradicting the decision:

1. **§9 and §10 of the same reconciliation report** — §9 still called the decision an MVP blocker
   "requires the formula decision (§8.1) first", and §10 still opened with "Resolve the Living Score
   authority (product decision)". Leaving them would have made the file argue with itself two
   screens below the resolution.
2. **`docs/PILOT_RUNBOOK.md`** — its ADR reading list is the operator's entry point and it already
   lists ADR-001/002/004; without ADR-005 an operator could read the deprecated legacy route as the
   authority.
3. **`valora-living-score/SKILL.md`** — the skill states the five-component formula as fact but never
   said it is the *accepted* authority or that it is unimplemented, which is exactly the ambiguity
   that created this conflict. Six lines, additive.
4. **`docs/progress/ai-4.md`** — that note (written earlier this session) declares the question open.

Each change is additive or a marked resolution; no historical finding was deleted. Say the word if
any of the four should be reverted.

## Open questions

1. **When is the Security component's input built?** Ship the Task 7 engine with Security as
   `insufficient_data`, or do Task 6's incident model first. This affects whether the AI-4 brief can
   ever explain a Security driver.
2. **What happens to the legacy score route in the UI?** It stays deprecated and isolated here. If
   the pilot frontend needs "estate health" before Task 7 ships, the answer must be an explicit empty
   state, not a renamed legacy number.
3. **Who signs off the normalization benchmarks** (1 day = 100 and ≥30 days = 0 for resolution;
   ≥5 complaints/unit; ≥15 incidents; the satisfaction mapping and the infrastructure blend)? They
   are product parameters, and they are currently fixed only by the skill file. Task 7 will bake them
   into `v1.0.0` snapshots — with `engine_version` as the escape hatch if they change.
4. **`docs/PROJECT_STATUS.md` overstates what exists for exactly this work — found while checking this
   decision, not fixed here.** Line 57 lists "domain entities (LivingScore, PropertyValuationSnapshot)"
   and line 98 ticks "LivingScore entity (`app/analytics/domain/entities.py`)". The real file contains
   one dataclass, `LegacyPropertyScoreEntity`, and **zero** matches for "snapshot" anywhere under
   `backend/app` (re-checked with `grep -rni "snapshot" app`). The engine and snapshot checkboxes on
   lines 99–103 are correctly unticked, so the tracker's *intent* is right and only its entity inventory
   is wrong. Left alone deliberately: correcting a tracker's history is a different change from
   recording this decision, and it is a stale-doc fix, not a code fix.
5. Unchanged from earlier sessions: root-level `CLAUDE_README.md`, `ARCHITECTURE_AND_DOMAIN.md` and
   `DEVELOPMENT_AND_VALIDATION.md` still do not exist (only `docs/EXECUTION_ROADMAP.md` does).
