# Living Score v1.0.0

The estate-level Living Score measures how well one South African private estate is
being run, over a rolling 90-day window, from data the estate already produces:
complaints, security incidents, work orders and resident ratings.

**Authority.** The formula is a product-owner decision recorded in
[ADR-005](ADR-005-Living-Score-Authority.md) and §8.1 of
`docs/progress/group8-vantage-reconciliation.md`. The backend service is the only
implementation of the maths; no client recomputes it. The earlier 40/30/30
per-property score (`LegacyPropertyScore`, `app/analytics/services/living_score_service.py`)
is **not** Living Score v1, is gated behind `ENABLE_LEGACY_ROUTES`, and is untouched by
this document.

- **Engine version:** `1.0.0` (`ENGINE_VERSION` in `app/analytics/engine/constants.py`)
- **Implementation:** `app/analytics/engine/` (pure, no database), persisted by
  `app/analytics/services/estate_living_score_service.py`
- **Window:** `[as_of - 90 days, as_of]`, **both ends inclusive** (D1)

## 1. The formula

Five components, each scoring 0–100, combined as a **weight average over the
components that are actually measurable**:

```
overall = Σ(weight_i × score_i) / Σ(weight_i)        for measured i only
```

| Component | Key | Weight | Scores 100 when | Scores 0 when |
|---|---|---|---|---|
| Resolution speed | `resolution` | **0.30** | average resolution ≤ 1 day | average resolution ≥ 30 days |
| Complaint frequency | `frequency` | **0.25** | 0 complaints per unit | ≥ 5 complaints per unit |
| Security | `security` | **0.20** | 0 incidents in the window | ≥ 15 incidents |
| Resident satisfaction | `satisfaction` | **0.15** | 5-star average | 1-star average |
| Maintenance completion | `infrastructure` | **0.10** | 100% completed, 5-star provider | 0% completed |

Per-component normalisation, from the inputs of the window:

- `resolution = 100 × (30 − avg_resolution_days) / (30 − 1)`
- `frequency = 100 × (1 − complaints_per_unit / 5)`, where `complaints_per_unit = complaints_created / unit_count`
- `security = 100 × (1 − incidents / 15)`
- `satisfaction = 100 × (avg_rating − 1) / (5 − 1)`
- `infrastructure = 0.70 × completed_percentage + 0.30 × provider_rating_score` (D4),
  where `provider_rating_score = 100 × (avg_provider_rating − 1) / (5 − 1)`. Without any
  provider rating in the window the blend is omitted and completion alone is used, and the
  explanation says so.

Every component score is clamped to `[0, 100]`.

`contribution_i = weight_i × score_i / Σ(weight)` is the component's share of the
overall score; `lost_points_i = weight_i × (100 − score_i) / Σ(weight)` is what it costs.
Both are computed from **unrounded** component scores, so they reconcile with the overall
figure. `drivers` is the measured components sorted by lost points, worst first, with the
fixed component order breaking ties.

## 2. The insufficient-data rule

VALORA never invents evidence. A component is scored only when there is enough of it to
mean something (D2), and a component with too little is reported as `insufficient_data`
with `score = null` — **never as a zero**.

| Component | Minimum evidence |
|---|---|
| `resolution` | ≥ 3 resolved complaints |
| `frequency` | ≥ 30 days of history **and** ≥ 1 unit |
| `security` | ≥ 30 days of history **and** ≥ 1 unit |
| `satisfaction` | ≥ 3 ratings |
| `infrastructure` | ≥ 1 work order in the window |

Across components (D3): if the measured weight is below **0.50**, the overall score is
`null` and the status is `insufficient_data`. A score can never be built from a sliver of
an estate's operations.

The `frequency` and `security` floors exist because zero activity in a brand-new estate is
not evidence of health; it is evidence of a short history.

Status vocabulary, fixed by the engine:

| Scope | Value | Meaning |
|---|---|---|
| component | `measured` | The component had enough evidence and carries a score. |
| component | `insufficient_data` | Not enough evidence; `score`, `contribution`, `lost_points` are `null`. |
| overall | `scored` | Measured weight ≥ 0.50; `overall_score` is a number. |
| overall | `insufficient_data` | Measured weight < 0.50; `overall_score` is `null`. |

## 3. The v1.0.0 decisions (D1–D6)

The specification did not fix these. They are recorded in
`app/analytics/engine/constants.py` and are part of the version.

- **D1 — Window.** `[as_of − 90 days, as_of]`, both ends inclusive. `window_bounds()` and
  `in_window()` are shared so the database layer does not re-derive the boundary.
- **D2 — Measurability.** The minimum-evidence table in §2.
- **D3 — Coverage floor.** `measured_weight < 0.50` means no overall score.
- **D4 — Infrastructure blend.** `0.70 × completion + 0.30 × provider rating`.
- **D5 — Rounding.** Components and the overall score round to 2 decimal places with
  `ROUND_HALF_UP`, always from unrounded intermediates, so nothing double-rounds.
- **D6 — Security is not size-normalised.** The skill asks for incidents "normalized by
  size" but gives no rule, so v1.0.0 scores the **raw estate incident count** against the
  documented 0–15 benchmark. No scaling was invented; sizing that benchmark is an open
  question for a future version.

## 4. Changing the algorithm means a new engine version

These rules **are** the version. Editing a benchmark, a weight, a floor or a rounding rule
without changing `ENGINE_VERSION` would silently move a number an estate has already seen
and acted on.

- A stored snapshot records the `engine_version` that produced it, together with its
  `as_of`, `window_start`, and the full explanation.
- Snapshots are **append-only**. A recalculation writes a new row; it never updates or
  deletes a stored one.
- Reads project the stored snapshot: `GET .../living-score` and `.../history` never
  recompute a past score. A historical value does not move when today's complaints,
  incidents, work orders or ratings change.
- Any change to the scoring rules must bump `ENGINE_VERSION` (for example `1.1.0`), leave
  existing rows readable at their own version, and be documented here.

## 5. API

All three routes are estate-scoped through the `estate_id` **query parameter**. The estate
is authorized against a persisted membership inside the service; a client-supplied
`estate_id` is never proof of access. A non-member gets `403`; an estate that belongs to
someone else behaves as if it does not exist (`404`). Reads are for any estate member;
recalculation needs the global `hoa_admin` role **and** membership of that estate.

| Method | Path | Who | Result |
|---|---|---|---|
| `GET` | `/api/v1/analytics/living-score?estate_id=` | member | The latest stored snapshot, full breakdown. `404` when the estate has never been scored. |
| `POST` | `/api/v1/analytics/living-score/recalculate?estate_id=` | `hoa_admin` + member | Calculates and appends a new snapshot. `201`. |
| `GET` | `/api/v1/analytics/living-score/history?estate_id=&page=&page_size=` | member | A page of stored snapshots, newest first. `page ≥ 1`, `1 ≤ page_size ≤ 100` (default 20). |

`404` for an unscored estate is deliberate: an empty or partial score would be read as a
health signal, and there is none yet.

The snapshot response carries `id`, `estate_id`, `engine_version`, `as_of`,
`window_start`, `calculated_at`, `status`, `overall_score` (null when insufficient),
`measured_weight`, `is_demo`, `components[5]` and `drivers[]`. Each component carries
`key`, `label`, `weight`, `status`, `score`, `inputs`, `benchmark`, `contribution`,
`lost_points`, `explanation` and `recommendation`. History rows are summaries only:
`id`, `as_of`, `window_start`, `status`, `overall_score`, `measured_weight`,
`engine_version`.

`is_demo` marks a seeded demonstration estate. It is read from the estate at response
time, not stored on the snapshot, so a snapshot never has to be rewritten.

Errors use the standard envelope (`{"detail": {"code", "message", "request_id"}}`):
`RESOURCE_NOT_FOUND`, `FORBIDDEN`, `UNAUTHENTICATED`, `VALIDATION_ERROR`.

The response contains no raw complaint text and no personal data: `inputs` are window
aggregates (counts, averages, coverage days, per-unit rates) and the advice is static text
from the engine's vocabulary. `calculated_by` is internal and is not part of the contract.

## 6. Scheduled recalculation

```text
python -m app.cli recalc-living-scores [--estate-id N] [--include-demo]
```

Appends one snapshot per selected estate, oldest estate id first, printing one line per
estate with its id, status, score and engine version. It prints operational metadata only —
never personal data — so a run can be logged as-is.

- **Real estates only by default.** A seeded demonstration estate is excluded unless
  `--include-demo` is passed.
- **No scheduler and no queue in the application.** The cadence belongs to a daily
  **Windows Task Scheduler** job that runs this command; the command itself is the hook.
- Re-running is safe for history: each run appends, and no stored snapshot is rewritten.

## 7. Not in v1.0.0

- Size-normalised security (D6) — see the open question above.
- Per-property or per-block scores; v1.0.0 is estate-level only.
- Any predictive or model-driven component. The engine is deterministic: the same inputs
  always produce the same snapshot, and the advice is static text.
