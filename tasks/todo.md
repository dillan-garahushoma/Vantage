# VALORA Core MVP Tasks

## Foundation

### Task 1: Establish backend test and configuration baseline ✅

**Acceptance criteria:**
- [x] Pytest and async test dependencies are declared.
- [x] Settings support explicit CORS origins and safe development defaults.
- [x] Shared error handling returns a consistent request-ID envelope.

**Verification (2026-10-06):** `pytest tests/test_api_error_contract.py -q` passed (2 tests); `python -m compileall -q app` passed; `flake8 app --count --select=E9,F63,F7,F82` reported 0 findings. Existing FastAPI lifecycle and upstream TestClient warnings remain for later framework maintenance.

**Verify:** Focused configuration/error tests pass; compile and lint remain clean.

**Dependencies:** None

### Task 2: Add estate tenancy and property membership persistence

**Acceptance criteria:**
- [x] Estates and explicit user-property/estate membership records are migrated.
- [x] Existing property records can be scoped to an estate.
- [x] Repository contracts load only scoped records.

**Verification (2026-10-06):** Model/repository and API-contract tests passed (5 tests); byte compilation and syntax-focused Flake8 passed. The migration has been validated through Alembic's offline SQL generation. Docker/PostgreSQL are unavailable on this workstation, so applying it to a live empty database remains part of the later clean-start acceptance run.

**Verify:** Migration upgrades an empty database; repository tests prove membership lookup.

**Dependencies:** Task 1

### Task 3: Restrict registration and establish estate authorization

**Acceptance criteria:**
- [x] Public registration creates a resident only.
- [x] HOA/provider capability requires an explicit existing membership/profile.
- [x] Cross-estate/property access is forbidden.

**Verification (2026-10-06):** Nine focused backend tests passed. The registration DTO rejects a supplied role, the application service always creates residents, and the estate authorization service rejects missing/capability-mismatched memberships. Property reads and creation require persisted estate membership and are estate-filtered at repository level. The earlier verification did not establish that malformed JWT subjects return 401; that behavior was corrected and explicitly tested in Hardening pass H, Batch A.

**Dependencies:** Task 2

## Hardening pass H — Phase 0

**Status:** Batches T and A–F implemented. See `docs/progress/phase0-partial.md` and the per-batch reports for exact verification evidence and remaining database gates.

- [x] Add a test harness that skips integration tests without `TEST_DATABASE_URL` and refuses database names without `test`.
- [x] Return the standard 401 envelope for malformed, missing, expired, tampered, and deleted-user JWT cases; reject privileged registration roles.
- [x] Resolve tenant authorization from estate memberships and enforce estate/resource scoping.
- [x] Preserve complaint/work-order state integrity and make resident rating the single writer of the provider rating aggregate.
- [x] Add database integrity constraints and verify offline Alembic SQL through `d4a7e1c9b3f2`.
- [x] Gate legacy listing, sales, provider review/write, and score routes by default.
- [x] Add CI test, compile, offline migration, and flake8 steps; constrain CI installs from the known-good backend environment.
- [x] Put the frontend behind the Compose `frontend` profile and configure the API's explicit CORS origins.
- [x] Document estate authorization, legacy isolation, rating writes, and the anonymity limitation.
- [x] Run integration tests against disposable PostgreSQL and apply migrations to a clean/live test database.
  (Done repeatedly since: throwaway databases migrated from empty with `alembic upgrade head`, integration suites run against them, and the head re-checked with `alembic heads` / `alembic current` — most recently on `valora_demo_test_20261012`, `2026-10-12`.)

**Known anonymity limitation:** An anonymous complaint's author ID is scrubbed from event responses for other viewers, but the HOA can still infer the author from `unit_id`.

**Contract notes:** Invalid lifecycle transitions use 409 Conflict rather than 403 Forbidden. Legacy routes are absent from OpenAPI and return 404 by default. Provider profile reads are limited to an HOA administrator with estate membership or the provider reading their own profile.

**Verification:** The checkboxes above reflect implementation evidence; the full suite and Batch F CI-equivalent commands are recorded in `docs/progress/phase0-F.md`. Integration database tests and a live migration apply remain unrun.

## Operational loop

### Task 4: Preserve the complaint lifecycle as events

**Acceptance criteria:**
- [x] Complaint creation creates a submitted event.
- [x] HOA review and assignment transitions are guarded and timestamped.
- [x] Residents and HOA users see only their authorized estate scope.

**Verification (2026-10-06):** Twelve focused backend tests pass. Complaint creation writes a submitted event in the same persistence operation; the state graph permits submitted → reviewed → assigned → in progress → resolved; transition timestamps and append-only evidence are persisted. Complaint queries and stats require an estate membership and filter by estate.

**Dependencies:** Task 3

### Task 5: Complete provider work-order execution and resident rating

**Acceptance criteria:**
- [x] HOA assignment creates an estate-scoped work order.
- [x] Only the linked provider can update its assigned work order.
- [x] A completed work order accepts one rating from its originating resident.

**Verification (2026-10-06):** Fourteen focused backend tests pass. Work orders carry their estate; provider profiles can be linked to one authenticated user; only that user can update progress/completion. Provider progress/completion writes the corresponding complaint lifecycle event, while resident ratings remain one-per-completed-work-order and are estate-scoped.

**Dependencies:** Task 4

### Task 6: Add estate announcements and security incidents

**Acceptance criteria:**
- [x] Announcements and incidents are estate-scoped.
- [x] HOA can manage them; estate members can view valid announcements.
- [x] Incident fields support score inputs without becoming a security platform.

**Verification:** Both resources carry `estate_id`, are created and read through the `estate_id` query parameter, and are authorized by `EstateAuthorizationService` against a persisted membership; the repositories expose no unscoped read. `tests/test_announcements_estate_scoping.py` and `tests/test_security_incidents.py` cover the scoping, the role gates and the incident vocabulary, and both were run in the BATCH 7C session (see `docs/progress/batch-7c.md` for the exact command and counts). Incident fields (`severity`, `category`, `status`, `occurred_at`, `resolved_at`) are the score inputs; there is no case management, evidence store or alerting. Integration cases in both files skip without `TEST_DATABASE_URL`.

**Verify:** API authorization and filtering tests pass.

**Dependencies:** Task 3

### Task 7: Implement Living Score v1.0.0 and immutable history

**Acceptance criteria:**
- [x] The five documented components use a 90-day estate window and bounds.
- [x] Each calculation persists a versioned snapshot and returns explanation data.
- [x] The history API returns snapshots without recalculating their past values.

**Verification:** Implemented as engine `1.0.0` in `app/analytics/engine/` over `[as_of - 90 days, as_of]` inclusive, with the formula, the D1–D6 decisions and the insufficient-data rule written up in `docs/LIVING_SCORE_V1.md`. `tests/test_living_score_engine.py`, `tests/test_living_score_snapshots.py` and `tests/test_living_score_api.py` cover normal, boundary, missing-data, cutoff, repeatability and version cases; the three Living Score routes are `GET /api/v1/analytics/living-score`, `POST .../recalculate` (201) and `GET .../history`, and the reads project the stored snapshot rather than recomputing it. Snapshots are append-only; changing the algorithm requires a new `ENGINE_VERSION`. `python -m app.cli recalc-living-scores` is the scheduled hook (real estates only by default). See `docs/progress/batch-7c.md` for the exact commands and counts.

**Verify:** Unit tests cover normal, boundary, missing-data, cutoff, repeatability, and version cases.

**Dependencies:** Tasks 5 and 6

### Checkpoint: Backend core

- [x] Migrations, auth, lifecycle, score, and authorization tests pass.
- [x] Seeded core vertical slice works through the API.

**Verification (2026-10-12):** an earlier sitting ran the whole suite against a throwaway
PostgreSQL (`814 passed, 0 failed, 0 skipped`); this sitting re-ran the P1/P2/P4 files
(`49 passed in 159.51s`) and the live journey against the seeded demo estate. **Caveat:**
today's full-suite re-run reported 11 errors at ~26 % and was stopped when the session ran
out of time, so the full suite must be re-run before this line is treated as re-confirmed on
the current tree — see `docs/progress/onb-master.md`, "Still outstanding".

## Product client

### Task 8: Create the frontend foundation and typed API boundary

**Acceptance criteria:**
- [x] Vite/React/TypeScript client builds from the repository.
- [x] Session and typed API client handle loading, API error, unauthorized, and network error states.
- [x] Public landing, login, and registration screens are accessible and responsive.

**Verification (2026-10-12):** `npm run build` → `BUILD_EXIT=0`, 82 modules, built in 1m 13s
(and the same build inside the Docker frontend image); `npm run typecheck` clean;
`npx vitest run` → 20 files / 142 tests passed; `npm run check:api` → the generated types
match `docs/openapi.json`. The responsive claim is measured — the mocked sweep asserts
`scrollWidth == clientWidth` on 16 routes at 390 × 844, and the live journey measured
390 == 390 on the complaints register and the dashboard with real data.

**Verify:** Frontend unit tests and production build pass.

**Dependencies:** Task 3

### Task 9: Deliver the resident operational experience

**Acceptance criteria:**
- [x] Resident can view estate context, Living Score, announcements, and own complaints.
- [x] Resident can report a complaint, view its event history, and rate completion.
- [x] Empty, validation, loading, error, and forbidden states are rendered deliberately.

**Verification (2026-10-12):** the dashboard now renders the **stored** Living Score snapshot
(`Dashboard.livingScore.test.tsx`, 5 tests, including the "not enough data yet" state and the
refused recalculation); the resident's complaint drawer covers logging, the append-only
event history and rating a completed work order (`ComplaintDrawer.test.tsx`,
`ComplaintDrawer.refresh.test.tsx`); and the live journey drove the resident through
logging, watching the repair, and rating it against the seeded estate. States are pinned by
the `e2e/mobile.spec.ts` sweep and the per-screen specs (`Join`, `Register`, `AdminSetup`,
`ProviderWork`, `publicDirectory`).

**Verify:** Component tests and browser flow against seeded backend pass.

**Dependencies:** Tasks 5, 7, and 8

### Task 10: Deliver HOA and provider operational experiences

**Acceptance criteria:**
- [x] HOA can review, assign, and monitor estate work.
- [x] Provider can view only assigned work and update progress/completion.
- [x] Score explanation/history supports practical HOA action.

**Verification (2026-10-12):** the live journey passed end to end through the UI — the HOA
marked the complaint under review, assigned a member provider (which created the work order),
recalculated the Living Score, and the dashboard showed the stored number; the provider saw
their own job and made exactly the two permitted transitions
(`ProviderWork.test.tsx` + `work-order-journey.spec.ts`, desktop and mobile). The Living Score
panel explains the five components, their weights and the engine version, and the admin
register (`/admin/members`) adds a provider by email.

**Verify:** Role-navigation tests and browser flow pass.

**Dependencies:** Tasks 5, 7, and 8

## Acceptance and handover

### Task 11: Add deterministic seed data and operational documentation

**Acceptance criteria:**
- [x] Seed data creates a coherent South African estate narrative and demo accounts.
- [x] Local setup, migration, seed, API, score, and known limitations docs are current.
- [x] No frontend-only operational metric is required to populate the product.

**Verification (2026-10-12):** `python -m app.cli seed-demo --expect-database valora_demo`
creates one estate with 120 days of history, 24 units, 20 residents, 2 member providers,
36 complaints in every lifecycle state with matching events, work orders with ratings,
incidents, announcements, 5 photographs through the real upload pipeline and 4 **real**
engine snapshots — guarded, deterministic, idempotent, and it never seeds AI output
(`test_onb_master_p4_demo_seed.py`, 10 tests; `test_seed_demo_flag.py`, 2).
[README.md](../README.md), [GETTING_STARTED.md](../docs/GETTING_STARTED.md),
[KNOWN_LIMITATIONS.md](../docs/KNOWN_LIMITATIONS.md) and [PILOT_RUNBOOK.md](../docs/PILOT_RUNBOOK.md)
are current for this tree; every number the product shows comes from backend records.

**Verify:** Clean seed execution and documented demo login checks pass.

**Dependencies:** Tasks 7 through 10

### Task 12: Run final product quality gates

**Acceptance criteria:**
- [x] Automated test/build evidence is recorded.
- [ ] Desktop/mobile browser QA, security review, performance inspection, and code review are complete.
  (Desktop and mobile browser QA **is** done — the live journey at 1440 px and 390 px plus the
  16-route overflow sweep — and the security review was done in the earlier batches. The line stays
  unticked because **no performance inspection or load test has been run**, and no formal code
  review is recorded for this sitting.)
- [x] Blocking limitations are explicit in documentation and handover.
  (See [KNOWN_LIMITATIONS.md](../docs/KNOWN_LIMITATIONS.md) — 18 entries — and the "What is NOT ready"
  section of `docs/progress/onb-master.md`.)

**Verify:** Full acceptance path from seeded clean startup is executed where local services are available.

**Dependencies:** Task 11
