# ADR-005: Living Score Authority

## Status

Accepted. Product-owner decision recorded 2026-10-10. Supersedes the open conflict
recorded as §8.1 of `docs/progress/group8-vantage-reconciliation.md`.

## Context

Two different scoring models both claimed the name "Living Score", and the tree
contained only the older one:

1. **The legacy per-property score.** `LegacyPropertyScoreService` /
   `LegacyPropertyScoreRepository` / `LegacyPropertyScoreResponse` in
   `backend/app/analytics/` compute a 40/30/30 blend of community health,
   maintenance and provider reliability for a single `unit_id`, on the fly, and
   never persist it. It has no `estate_id`, no rolling window and no version
   string.
2. **The documented five-component estate score.**
   `.agents/skills/valora-living-score/SKILL.md` specifies a deterministic,
   estate-level `v1.0.0` engine over a rolling 90-day window, with an immutable
   `LivingScoreSnapshot` carrying `engine_version`.

`docs/progress/group8-vantage-reconciliation.md` §8.1 froze the choice: the
five-component formula must **not** be implemented until the product owner
confirmed which model was authoritative, and no blending was to be performed.
That freeze also blocked Task 7 (which the AI-4 batch lists as its prerequisite)
and, through it, the AI Health Brief.

`docs/SPEC-VALORA-MVP-CORE.md` already anticipated the answer — it records that the
existing property-only 40/30/30 score "has no rolling window or snapshots" and
that it should be superseded by "the documented estate-level five-component
deterministic `v1.0.0` score".

## Decision

**The five-component, estate-level Living Score `v1.0.0` is the authoritative
score.** Living Score is defined over a rolling **90-day** window as:

| Component | Weight | Target metric |
| --- | --- | --- |
| Resolution | 0.30 | Average complaint resolution days (1 day = 100, ≥30 days = 0) |
| Frequency | 0.25 | Complaints per unit in 90 days (0/unit = 100, ≥5/unit = 0) |
| Security | 0.20 | Security incidents normalised by estate size (0 = 100, ≥15 = 0) |
| Satisfaction | 0.15 | Average resident rating on closed work orders (1.0–5.0 → 0–100) |
| Infrastructure | 0.10 | Resolved-vs-open work orders blended with provider ratings |

Every sub-score and the composite are clamped to `[0.0, 100.0]`. The calculation is
strictly rule-based and deterministic: identical operational inputs must produce an
identical score, and no black-box or non-deterministic heuristic may be introduced in
the MVP phase. Every computation persists an **immutable** `LivingScoreSnapshot`
carrying `engine_version` (`v1.0.0`), so evolving the algorithm cannot retroactively
change historical values.

**The legacy 40/30/30 per-property score is not Living Score v1.** It stays isolated
exactly as ADR-003 left it: named `LegacyPropertyScore*`, reachable only through the
deprecated, estate-authorized property route, and gated with the other legacy
surfaces. It must **not** be extended, re-weighted, or presented to users as Living
Score, and its values must never be blended into, migrated into, or used to backfill a
snapshot. `AIAnalytic` and the other legacy valuation fields are unrelated to this
decision and remain untouched.

## Consequences

- The formula authority is settled, so Task 7 (estate snapshot model, 90-day
  calculation, versioned history API) is no longer blocked by a product question and
  can be implemented as specified. **This ADR does not implement it.** No snapshot
  model, table, service or endpoint exists in the tree as of this record.
- The AI Health Brief (BATCH AI-4) remains blocked: its `BriefFacts` are defined
  component-by-component off the snapshot, so it still needs Task 7's real field
  names. It is no longer blocked by the authority question, only by the missing code.
- The Security component needs a source of incidents. Security incidents are also
  absent from the tree (Task 6 is unticked), so that sub-score will read
  `insufficient_data` until an incident model exists. That is now a data-availability
  gap, not a formula ambiguity.
- Because the legacy score is explicitly **not** upgraded, residents must not be shown
  a mixed or renamed view: today the only wired score route is the deprecated legacy
  one, and it should stay labelled as legacy until Task 7 ships the estate score.
- Historical comparability: the first `v1.0.0` snapshot is the beginning of the
  series. There is no legitimate predecessor value, and none should be fabricated.

## Verification and follow-ups

- Recorded here and in `docs/progress/group8-vantage-reconciliation.md` §8.1; the
  narrative of this decision is in `docs/progress/score-authority.md`.
- **No code, migration, model, endpoint or test was changed by this decision.** The
  existing suite is unaffected.
- Follow-up: implement Task 7 (five-component engine, 90-day window, immutable
  versioned snapshots, history API) as its own batch, with failing tests first.
- Follow-up: add the estate-scoped security-incident model (Task 6) so the Security
  component has an input, or consciously ship it as `insufficient_data`.
- Follow-up: re-issue BATCH AI-4 unchanged once Task 7 lands; its template brief and
  grounding validator already assume exactly this shape.
