---
name: valora-living-score
description: Encodes the deterministic Living Score algorithm, rolling 90-day calculation, normalization rules, and snapshot immutability for VALORA. Use when calculating, testing, or explaining estate health metrics.
---

# VALORA Living Score Engine

> **Authority:** this five-component, estate-level `v1.0.0` formula is the accepted
> Living Score definition (product-owner decision recorded in
> `docs/ADR-005-Living-Score-Authority.md`). The legacy 40/30/30 per-property score
> in `backend/app/analytics/` is **not** Living Score v1 — it stays isolated as
> `LegacyPropertyScore*` and must not be extended, blended into a snapshot, or
> presented to users as Living Score. As of that decision the engine described below
> is **not yet implemented**: no snapshot model, table or history API exists.

The **Living Score** is VALORA's core differentiator. It quantifies the operational health and livability of an estate into a transparent, bounded index between `0` and `100`.

## Mathematical Formula

The score is calculated over a rolling **90-day window**:

$$\text{Living Score} = (0.30 \times S_{\text{resolution}}) + (0.25 \times S_{\text{frequency}}) + (0.20 \times S_{\text{security}}) + (0.15 \times S_{\text{satisfaction}}) + (0.10 \times S_{\text{infrastructure}})$$

### Component Weights & Sub-scores

| Component | Weight | Target Metric | Normalization Formula |
|---|---|---|---|
| **$S_{\text{resolution}}$** | 0.30 | Average complaint resolution days | Benchmark: 1 day = 100, $\ge$ 30 days = 0. Min-max normalized. |
| **$S_{\text{frequency}}$** | 0.25 | Complaints per unit in 90 days | Benchmark: 0/unit = 100, $\ge$ 5/unit = 0. Inverse min-max. |
| **$S_{\text{security}}$** | 0.20 | Security incidents normalized by size | Benchmark: 0 incidents = 100, $\ge$ 15 incidents = 0. Inverse min-max. |
| **$S_{\text{satisfaction}}$** | 0.15 | Average resident rating on closed work orders | 1.0 to 5.0 scale mapped linearly to 0–100. |
| **$S_{\text{infrastructure}}$** | 0.10 | Ratio of resolved vs. open work orders + provider ratings | Percentage resolved (0-100) blended with contractor score. |

## Mandatory Engine Requirements

1. **Deterministic Rule Engine (MVP):**
   - Must be strictly rule-based and deterministic.
   - Do **NOT** use black-box machine learning or non-deterministic heuristics for this calculation during the MVP phase.
   - The same operational input data must yield the exact same score every time.

2. **Bounded Scores:**
   - Every sub-score $S_i$ and the total composite Living Score must be strictly clamped to `[0.0, 100.0]`.

3. **Explainability & Breakdown:**
   - The calculation service must return both the composite score and a granular breakdown:
     - Component sub-scores
     - Positive and negative contributing factors
     - Recommendations for HOA management

4. **Historical Snapshots & Versioning:**
   - Whenever a score is recomputed, save an immutable record in `LivingScoreSnapshot`.
   - Record `engine_version` (e.g. `v1.0.0`) with each snapshot to allow algorithm evolution without corrupting historical records.

5. **Exhaustive Unit Tests:**
   - Unit tests must cover boundary values: zero complaints, maximum complaints, all 1-star ratings, all 5-star ratings, missing data fallback, and 90-day time filtering.
