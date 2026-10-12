# BATCH 7A — Living Score v1.0.0 pure calculation engine

**Date:** 2026-10-10 · **Scope:** `app/analytics/engine/` only. No DB, no endpoints,
no migration, no ORM import, legacy property score untouched.

## Prerequisite check (batch requirement: verify, stop if missing)

The batch is gated on the score-authority decision being recorded in the
reconciliation report §8.1. Verified in the working tree before writing code:

```
docs/progress/group8-vantage-reconciliation.md:187
  1. **Living Score formula conflict — RESOLVED 2026-10-10 by product-owner ...
docs/ADR-005-Living-Score-Authority.md   (present)
```

§8.1 is RESOLVED and ADR-005 carries the five-component, estate-level v1.0.0
formula, so the batch was allowed to proceed. No stop condition triggered.

## Done

| File | Contents |
|---|---|
| `backend/app/analytics/engine/constants.py` | Version, fixed component order, weights (0.30/0.25/0.20/0.15/0.10), benchmarks, measurability minimums, recommendation text, and decisions **D1–D6** as commented module constants. |
| `backend/app/analytics/engine/models.py` | Frozen dataclasses `EstateScoreInputs`, `ComponentResult`, `ScoreResult`. |
| `backend/app/analytics/engine/living_score.py` | The five pure component functions, `window_bounds`, `in_window`, `calculate_living_score`, `describe_component`. |
| `backend/app/analytics/engine/__init__.py` | Public surface: the two entry points plus the constants a caller/snapshot writer needs. |
| `backend/tests/test_living_score_engine.py` | 43 tests, written **before** the engine (first run was `ModuleNotFoundError`, as required). |

Engine properties, all enforced by tests rather than by convention:

- **No clock.** `as_of` is a parameter; `window_bounds`/`in_window` derive the
  window from it only. A test asserts shifting `as_of` by 1 day and by 10 years
  moves the window by exactly that amount.
- **No database / no ORM.** The import closure of the package is stdlib only
  (`dataclasses`, `datetime`, `decimal`, `typing`) plus its own modules. A test
  asserts the absence of `sqlalchemy`, `app.db`, `app.analytics.repositories`,
  `app.analytics.models`, clock reads and `float(`.
- **Decimal only.** No float arithmetic anywhere; `EstateScoreInputs` raises
  `TypeError` if an average arrives as a `float`. Rounding happens once, at the
  boundary, `ROUND_HALF_UP` to 2 dp, computed from unrounded intermediates.
- **Total, never raising on missing data.** A component with too little evidence
  is `insufficient_data` with `score`/`contribution`/`lost_points` `= None` (never
  0, which would read as a real measurement of zero).

### Decisions recorded for v1.0.0 (batch asked for these in `constants.py`)

- **D1** window `[as_of - 90d, as_of]`, **both ends inclusive**; exported as
  `window_bounds()` and `in_window()` so the DB layer reuses one definition.
- **D2** measurability: resolution ≥ 3 resolved; frequency and security need
  `coverage_days ≥ 30` **and** `unit_count ≥ 1`; satisfaction ≥ 3 ratings;
  infrastructure ≥ 1 work order.
- **D3** overall is `None`, status `insufficient_data`, when measured weight < 0.50.
- **D4** infrastructure = 0.70 × completion pct + 0.30 × provider rating score;
  provider half omitted (with the reason stated in the explanation) when no
  provider ratings exist.
- **D5** round components and overall to 2 dp `ROUND_HALF_UP` from unrounded
  intermediates.
- **D6** security scores the **raw** estate incident count against the 0–15
  benchmark. The skill says "normalized by size" but gives no rule; no scaling
  was invented. **Open question** (below).

## Tests added and passing

`backend/tests/test_living_score_engine.py` — 43 tests: `43 passed in 0.22s`.

Hand-computed normal case (`20 complaints / 50 units`, 6-day average resolution,
4.5-star average): resolution 82.76, frequency 92.00, security 80.00,
satisfaction 87.50, infrastructure 75.00, overall **84.45**, measured weight 1.00.
Contributions and lost points are asserted and shown to reconcile with the
overall score. Renormalisation case (0.75 measured weight) asserted end to end:
scores, contributions (20.00 / 33.33 / 26.67), lost points and overall 80.00.

Also covered, as the batch listed: every component at 0, at 100 and beyond
benchmark (clamped, not wrapped); all-1-star → 0 / all-5-star → 100; zero
complaints with coverage ≥ 30 → 100 and with coverage < 30 → insufficient; no
resolved complaints → insufficient without raising; measured weight 0.45 → overall
`None` and 0.55 → scored; window boundaries (exactly 90 days in, 90 days + 1 µs
out, future out, naive timestamps treated as UTC); determinism (100 identical
runs, plus repeated calls returning equal-but-distinct objects); every number is a
`Decimal`; 250 seeded random input sets staying inside `[0, 100]`; extreme inputs
(10⁹ counts) neither raising nor overflowing; `ENGINE_VERSION == "1.0.0"`.

### Mutation check (proving the suite has teeth)

Each mutation was applied, the suite run, and the source restored (`diff` against
a backup confirmed clean restoration afterwards):

| Mutation | Result |
|---|---|
| Resolution denominator 29 → 30 | 5 failed |
| D3 floor 0.50 → 0.60 | 1 failed (`..._above_the_measured_weight_floor...`) |
| Window end becomes exclusive | 1 failed (`..._window_membership_boundaries`) |
| Recommendation threshold 70 → 0 | 1 failed |
| Contribution denominator `measured_weight` dropped | 1 failed |
| Lost-points denominator `measured_weight` dropped | 1 failed |
| Drivers sorted ascending | 2 failed |
| Per-component clamp removed in `_security` | **43 passed — no behaviour change** |

The last row is expected, not a gap: the aggregator re-clamps every measured
score at the boundary (`_round2(_clamp(...))`), so the per-component clamp is
defence in depth and removing either guard alone leaves the output identical. The
clamp itself is covered by the benchmark tests (incidents 15 → 0.00, 60 → 0.00;
rating 6 → 100.00).

The contribution/lost-points denominators were initially **untested**: the only
assertions on them used a measured weight of exactly 1.00, where dividing by
`measured_weight` is a no-op, so dropping the denominator passed the suite. Two
assertions on the renormalised case were added and both mutations then failed, as
the table shows.

## Full verification run (exact commands, results)

```
backend\venv\Scripts\python.exe -m pytest backend/tests -q
  -> 399 passed, 21 skipped, 4 warnings in 33.31s
backend\venv\Scripts\python.exe -m compileall -q backend/app
  -> OK (no output)
backend\venv\Scripts\python.exe -m flake8 backend/app backend/tests \
    --count --select=E9,F63,F7,F82 --show-source --statistics
  -> 0
git diff --check
  -> clean
```

The 21 skips are the integration tests that require `TEST_DATABASE_URL`; it is not
set in this terminal, so they skipped. **Not counted as passes.** This batch added
no database surface, so nothing it delivers is exercised by them.

## Legacy isolation

`app/analytics/services/living_score_service.py`, `app/analytics/models/ai_analytic.py`
and `app/analytics/schemas/living_score.py` are unmodified (`git status` clean for
all three). The new package shares no module, type or constant with the legacy
40/30/30 per-property score and imports nothing from it.

## Written but not run

Nothing. There is no migration, endpoint, seed or script in this batch, and every
artifact it does deliver was executed by the commands above.

## Remaining (deliberately out of scope for 7A)

- Snapshot model, table, migration and history API — the engine is pure and
  stateless; persistence is a later batch.
- The DB layer that aggregates rows into `EstateScoreInputs` (it must filter with
  `in_window`/`window_bounds` from this package rather than re-deriving the window).
- Wiring an engine result into an API response DTO.

## Open questions

1. **Security has no size normalisation (D6).** The skill says incidents are
   "normalized by size" but supplies no rule. v1.0.0 scores the raw estate count
   against 0–15, which is unfair to large estates and generous to small ones. A
   per-unit (or per-100-unit) benchmark needs a product decision; changing it means
   a **v1.1.0** engine version, not an edit of stored v1.0.0 snapshots.
2. **`coverage_days` is caller-supplied.** The engine trusts it rather than
   deriving it from the window; the DB aggregation layer must clamp it to
   `[0, 90]` so a caller cannot widen its own evidence base.
3. **Rounding drift is bounded, not zero.** Component scores are rounded for
   display while the overall uses unrounded values, so the displayed components can
   differ from the overall by up to ~0.05. A test asserts that bound; whether the
   UI should present the sum-of-rounded or the unrounded overall is a product call.
