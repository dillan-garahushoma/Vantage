# VALORA Next Build Roadmap

## Source Summary

This roadmap is based on the VALORA docs in `C:\Users\garah\PycharmProjects\VALORA\docs` and the current code in this repo.

The docs define VALORA as a Property Health Intelligence Platform for private residential communities. The core product thesis is:

```text
Community Events -> Community Health -> Living Score -> Property Intelligence
```

The MVP should prove one loop:

```text
Resident logs complaint
    -> HOA reviews and assigns provider
    -> Provider completes work order
    -> Resident rates resolution
    -> Living Score updates
    -> Valuation uses Living Score
```

Anything that does not support that loop should be deferred.

## Current Project State

### Frontend

The frontend currently has a usable authentication shell:

- Login page.
- Registration page.
- Four roles: resident, investor, estate agent, HOA admin.
- Mock authentication mode.
- API-ready authentication service.
- Protected `/app` route.
- Account summary and logout.

Verification result:

- `npm run test:phase3` passes.
- `npm run test:phase6` passes.
- Full `npm test` currently fails because `FrontEnd/FRONTEND_ACCEPTANCE_CHECKLIST.md` is missing and `tests/phase7-hardening.test.mjs` expects it.

### Backend

The backend has model drafts for users, properties, complaints, work orders, providers, announcements, listings, reviews, sales, sessions, login attempts, and AI analytics.

However, it is not currently startable:

- `app/main.py` imports `app.database`, but the importable source file does not exist as `app/database.py`.
- `app/main.py` imports `app.routes`, but the current repo has `app/routers/*` placeholder files instead.
- Several router and service files are only 2 bytes, meaning they are effectively empty placeholders.
- There is a split between `app/shared/*` and older `app/config`, `app/database` extensionless files.
- `app/models/__init__.py` imports `.ai_analtics`, but the actual file is `ai_analytic.py`.
- Several relationships are not enforced yet, for example complaint `unit_id` and work order `provider_id`.

The first backend priority is therefore not another feature. It is making the API import, boot, migrate, and expose one real vertical slice.

## Build Order

## Phase A - Stabilize The Platform

Goal: make the project runnable before adding domain behavior.

1. Choose one backend structure and remove the split.
   - Recommended: use the simpler current structure for now: `app/shared`, `app/models`, `app/routers`, `app/services`.
   - Create real `.py` router/service modules instead of extensionless placeholders.
   - Update `app/main.py` to import from modules that actually exist.

2. Fix backend import/startup.
   - Replace `from app.database import ...` with `from app.shared.database import ...`, or create a proper `app/database.py`.
   - Replace `from app.routes import ...` with real router imports.
   - Fix `ai_analtics` typo in `app/models/__init__.py`.
   - Decide sync SQLAlchemy or async SQLAlchemy; do not mix both in the same foundation.

3. Restore migration discipline.
   - Stop using `Base.metadata.create_all(bind=engine)` as the normal startup path.
   - Generate and review Alembic migration for the current MVP tables.
   - Apply migration to a fresh local database.

4. Restore frontend test green.
   - Add `FrontEnd/FRONTEND_ACCEPTANCE_CHECKLIST.md` with FE-01 through FE-10 checked, or update the test if the checklist requirement is no longer desired.

Acceptance criteria:

- Backend imports successfully with `python -c "import app.main"`.
- API starts with FastAPI/Uvicorn.
- `/health` returns 200.
- Frontend `npm test` passes.
- Swagger loads.

## Phase B - Real Authentication And RBAC

Goal: replace mock-only auth with working backend auth so all future role workflows are protected.

Build:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- Password hashing.
- JWT creation and verification.
- Role guard dependency.
- Unique email validation.

Roles:

- `resident`
- `investor`
- `estate_agent`
- `hoa_admin`
- Add `service_provider` before work orders are assigned directly to provider accounts.

Acceptance criteria:

- Register creates a user with a hashed password.
- Duplicate email returns 409.
- Login returns bearer token.
- `/me` returns the authenticated user.
- Protected routes return 401 without token.
- Role-protected routes return 403 for the wrong role.
- Frontend can run with `VITE_USE_MOCK_AUTH=false`.

## Phase C - Property And Estate Foundation

Goal: create the single-complex MVP data foundation.

Build:

- Estate model, even if MVP supports only one estate.
- Property/unit model linked to estate.
- Resident assignment to unit/property.
- HOA admin scoped to the estate.
- Seed/import path for HOA-provided property data.

Minimum tables:

- `estates`
- `properties` or `units`
- `users`
- `resident_units` if a user can be linked to more than one unit.

Acceptance criteria:

- HOA admin can create or import units.
- Resident account can be linked to a unit.
- Resident can view their property profile.
- Investor/agent can view read-only basic property data.

## Phase D - Complaint Lifecycle MVP

Goal: build the main operational signal source for VALORA.

Build status flow:

```text
Logged -> Under Review -> Assigned -> In Progress -> Resolved -> Closed
                 -> Rejected
Resolved -> Reopened -> Assigned
```

Build APIs:

- Resident: create complaint.
- Resident: view own complaints.
- HOA admin: view estate complaint queue.
- HOA admin: review, reject, or assign provider.
- Service provider/HOA: mark in progress and resolved.
- Resident: close complaint and rate resolution.

Model fixes:

- Complaint must reference a valid unit/property.
- Complaint status should use an enum or constrained values.
- Add severity and category fields that match Living Score inputs.
- Add timestamps for each lifecycle milestone or a separate status history table.

Acceptance criteria:

- A complaint can move through the full lifecycle.
- Invalid status transitions are rejected.
- Residents cannot edit other residents' complaints.
- HOA admin can see all complaints for their estate.
- The lifecycle produces resolution time and rating data.

## Phase E - Service Providers And Work Orders

Goal: make complaints actionable and measurable.

Build:

- Provider registration or HOA-created provider records.
- HOA verification.
- Provider assignment to work orders.
- Completion notes.
- Resident rating and optional review.

Model fixes:

- `maintenance_work_orders.provider_id` must be a foreign key.
- Ratings should be bounded from 1 to 5.
- Provider average rating should be derived from reviews/work orders, not manually trusted.

Acceptance criteria:

- HOA admin can verify providers.
- HOA admin can assign a verified provider to a complaint.
- A work order is created from assignment.
- Provider completion updates complaint state.
- Resident rating feeds provider score and Living Score input.

## Phase F - Announcements

Goal: add the governance communication signal, but keep it simple.

Build:

- HOA admin creates announcements.
- HOA admin edits/archives announcements.
- Residents view active announcements.

Acceptance criteria:

- Only HOA admins can create announcements.
- Residents see only active estate announcements.
- Announcement activity can be counted later by analytics.

## Phase G - Living Score Engine

Goal: implement VALORA's differentiator before advanced AI.

Start with a deterministic rules engine using the PRD weights:

- Resolution time: 30%.
- Complaint frequency: 25%.
- Security incidents: 20%.
- Resident satisfaction: 15%.
- Infrastructure maintenance: 10%.

Build:

- `living_score_service`.
- Rolling 90-day score per estate.
- Score breakdown by component.
- Contributing factors text for explainability.
- Persisted score snapshots.

Acceptance criteria:

- Score can be calculated from seeded complaints/work orders.
- Score returns total, component scores, and factors.
- Empty or sparse data produces a clear fallback state.
- Score updates after a complaint is closed and rated.

## Phase H - Rule-Based Valuation Adjustment

Goal: connect community health to property intelligence without overbuilding ML.

Build:

- Basic valuation request.
- Store predicted market value snapshot.
- Apply rule-based adjustment from Living Score.
- Explain the adjustment.

Example:

```text
Base valuation: R1,200,000
Living Score: 86
Adjustment: +2.5%
Adjusted valuation: R1,230,000
Reason: Fast complaint resolution and high resident satisfaction.
```

Acceptance criteria:

- Valuation references a property and estate Living Score.
- Investor/resident/agent can view valuation based on role.
- Output includes explanation, not only a number.

## Phase I - Persona Dashboards

Goal: expose the completed MVP loop through role-specific views.

Build only after the backend loop works:

- Resident: property summary, submit complaint, complaint history, announcements, Living Score.
- HOA admin: complaint queue, provider verification, announcements, average resolution time.
- Investor: property valuation, Living Score, complaint trends.
- Estate agent: property profile/listing data and Living Score.

Acceptance criteria:

- Each dashboard is role-aware.
- No dashboard shows fake final metrics unless they come from backend data or a clear demo seed.

## Defer Until After MVP

Do not build these next:

- 10-year ROI projection.
- Rental yield.
- Suburb growth prediction.
- Property24 or external listing integrations.
- ML valuation model.
- Natural language insight chat.
- Multi-estate benchmarking.
- Push notifications.
- Levy/financial management.

These are valuable, but the docs repeatedly say the MVP must prove the operational data -> Living Score -> valuation loop first.

## Recommended Next Sprint

Sprint goal: "VALORA boots and authenticates against the real backend."

Tasks:

1. Fix backend module imports and startup.
2. Decide one database/config layer.
3. Implement real auth router endpoints.
4. Add auth tests.
5. Add missing frontend acceptance checklist so frontend tests pass.
6. Flip frontend to API auth locally and complete register/login/me flow.

Demo at sprint review:

```text
Start API
Start frontend
Register as Resident
Login
Open protected app page
Call /me with token
Show database user with hashed password
Run backend auth tests
Run frontend npm test
```

After that sprint, build the property/unit foundation, then complaints. Complaints are the first true VALORA product feature because they generate the signals that make Living Score possible.
