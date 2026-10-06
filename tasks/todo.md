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

**Verification (2026-10-06):** Nine focused backend tests pass. The registration DTO rejects a supplied role, the application service always creates residents, and the estate authorization service rejects missing/capability-mismatched memberships. Property reads and creation now require a persisted estate membership and are estate-filtered at repository level.

**Dependencies:** Task 2

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
- [ ] Announcements and incidents are estate-scoped.
- [ ] HOA can manage them; estate members can view valid announcements.
- [ ] Incident fields support score inputs without becoming a security platform.

**Verify:** API authorization and filtering tests pass.

**Dependencies:** Task 3

### Task 7: Implement Living Score v1.0.0 and immutable history

**Acceptance criteria:**
- [ ] The five documented components use a 90-day estate window and bounds.
- [ ] Each calculation persists a versioned snapshot and returns explanation data.
- [ ] The history API returns snapshots without recalculating their past values.

**Verify:** Unit tests cover normal, boundary, missing-data, cutoff, repeatability, and version cases.

**Dependencies:** Tasks 5 and 6

### Checkpoint: Backend core

- [ ] Migrations, auth, lifecycle, score, and authorization tests pass.
- [ ] Seeded core vertical slice works through the API.

## Product client

### Task 8: Create the frontend foundation and typed API boundary

**Acceptance criteria:**
- [ ] Vite/React/TypeScript client builds from the repository.
- [ ] Session and typed API client handle loading, API error, unauthorized, and network error states.
- [ ] Public landing, login, and registration screens are accessible and responsive.

**Verify:** Frontend unit tests and production build pass.

**Dependencies:** Task 3

### Task 9: Deliver the resident operational experience

**Acceptance criteria:**
- [ ] Resident can view estate context, Living Score, announcements, and own complaints.
- [ ] Resident can report a complaint, view its event history, and rate completion.
- [ ] Empty, validation, loading, error, and forbidden states are rendered deliberately.

**Verify:** Component tests and browser flow against seeded backend pass.

**Dependencies:** Tasks 5, 7, and 8

### Task 10: Deliver HOA and provider operational experiences

**Acceptance criteria:**
- [ ] HOA can review, assign, and monitor estate work.
- [ ] Provider can view only assigned work and update progress/completion.
- [ ] Score explanation/history supports practical HOA action.

**Verify:** Role-navigation tests and browser flow pass.

**Dependencies:** Tasks 5, 7, and 8

## Acceptance and handover

### Task 11: Add deterministic seed data and operational documentation

**Acceptance criteria:**
- [ ] Seed data creates a coherent South African estate narrative and demo accounts.
- [ ] Local setup, migration, seed, API, score, and known limitations docs are current.
- [ ] No frontend-only operational metric is required to populate the product.

**Verify:** Clean seed execution and documented demo login checks pass.

**Dependencies:** Tasks 7 through 10

### Task 12: Run final product quality gates

**Acceptance criteria:**
- [ ] Automated test/build evidence is recorded.
- [ ] Desktop/mobile browser QA, security review, performance inspection, and code review are complete.
- [ ] Blocking limitations are explicit in documentation and handover.

**Verify:** Full acceptance path from seeded clean startup is executed where local services are available.

**Dependencies:** Task 11
