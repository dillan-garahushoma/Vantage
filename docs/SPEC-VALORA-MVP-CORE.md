# Specification: VALORA Core Operational Intelligence MVP

## Objective

Build a complete, verifiable operational loop for a private South African residential estate: a resident reports an issue, an HOA administrator assigns a provider, the provider completes the work, the resident rates the outcome, and the estate Living Score updates from persisted operational signals.

The product is a Property Health Intelligence platform, not a listing marketplace or a generic help-desk. Success means the full role-based workflow operates against PostgreSQL through the React client, and the transparent Living Score explains the resulting estate health.

## Audit findings and engineering decisions

| Finding | Decision |
| --- | --- |
| The repository has a modular FastAPI scaffold with async repositories and JWT login, but no checked-in frontend. | Preserve the backend's domain-oriented structure and create the React/Vite client in this repository. |
| `backend/docker-compose.yml` mounts a missing `../FrontEnd` path. | Replace the stale frontend mount with the new checked-in frontend configuration. |
| Existing `properties` rows are unit-like and are not estate-scoped; users reference a free-text unit number. | Treat existing property records as the property/unit aggregate for compatibility, add estates and explicit membership/ownership links. Do not create a duplicate, semantically empty Unit table. |
| Complaints and work orders lack foreign keys/events and cannot support estate authorization or historical intelligence. | Add estate-aware foreign keys, event records, state transition rules, and lifecycle timestamps through migrations. |
| The existing score is property-only, uses unrelated 40/30/30 factors, has no rolling window or snapshots. | Supersede it with the documented estate-level five-component deterministic `v1.0.0` score; retain no fake AI inference. |
| Authentication allows self-registration into privileged roles; CORS permits credentials from every origin. | Public registration creates residents only; privileged roles and estate membership require seeded/admin provisioning. Configure explicit development origins and production configuration. |
| There are no executable tests and CI performs syntax-oriented flake8 checks only. | Add pytest, frontend tests, and CI commands that execute them. |

## Tech stack

- Backend: Python 3.10, FastAPI, Pydantic v2, SQLAlchemy async, Alembic, PostgreSQL 15.
- Frontend: React, TypeScript, Vite, browser-native fetch client, CSS variables and semantic components.
- Local runtime: Docker Compose for PostgreSQL, API, and the checked-in frontend.
- Testing: pytest with an isolated database strategy; Vitest and React Testing Library; browser flow verification using Chrome DevTools/Playwright.

## Commands

These commands will be finalized against the generated frontend and test configuration during implementation.

```powershell
docker compose -f backend/docker-compose.yml up --build
docker compose -f backend/docker-compose.yml exec api alembic upgrade head
docker compose -f backend/docker-compose.yml exec api python -m app.scripts.seed_demo
python -m pytest backend/tests -q
npm --prefix frontend run test
npm --prefix frontend run build
```

## Target structure

```text
backend/app/
  identity/       authentication, roles, estate memberships
  property/       estates and property/unit context
  community/      complaints, events, work orders, ratings, announcements
  providers/      provider profiles and execution authorization
  analytics/      security incidents, Living Score calculation and snapshots
  scripts/        deterministic development seed command
frontend/src/
  api/            typed API client and DTOs
  features/       auth, complaints, work orders, score, announcements
  components/     accessible shared UI
  pages/          public and role-specific screens
docs/             architecture, setup, scoring, seed, and known-limitations docs
```

## API contract

All product endpoints live under `/api/v1`, use Pydantic input/output DTOs, provide 1-based `page` and `size` pagination, and return consistent structured errors carrying a request ID. The first contracts are estate-scoped:

```text
POST   /auth/register                 public resident registration
POST   /auth/login                    JWT issue
GET    /auth/me                       authenticated profile and memberships
GET    /estates/{estateId}            authorized estate context
GET    /properties                    authorized estate properties
POST   /complaints                    resident submission
PATCH  /complaints/{id}/review        HOA transition to reviewed
POST   /complaints/{id}/work-orders   HOA provider assignment
PATCH  /work-orders/{id}/status       assigned provider progress/completion
POST   /work-orders/{id}/rating       originating resident feedback
GET    /living-score/estates/{id}     latest calculated score and breakdown
GET    /living-score/estates/{id}/history
```

## Domain and data rules

- Estate membership is the authorization boundary; an ID alone never grants access.
- `ComplaintEvent`, `Rating`, and `LivingScoreSnapshot` are append-only historical records.
- The complaint state machine is `submitted -> reviewed -> assigned -> in_progress -> resolved -> rated`, with explicit guarded transitions and timestamps.
- One complaint has one active work order in the MVP; reopening is intentionally out of scope until lifecycle evidence requires it.
- `SecurityIncident` is a focused estate operational record, not a full security-management system.
- Living Score uses a rolling 90-day window and the weights: resolution 0.30, frequency 0.25, security 0.20, satisfaction 0.15, infrastructure 0.10. Every component and total is clamped to `[0, 100]`.
- Missing observations use explicit neutral fallbacks in the returned explanation; null values never silently propagate into a score.

## Frontend requirements

- Public landing, login, and resident registration screens.
- Resident: dashboard, complaint list/detail/reporting, work-order rating, announcement and score views.
- HOA: operational dashboard, complaint review/assignment, provider/work-order management, announcements, score breakdown/history.
- Provider: assigned-work list, work-order detail, progress and completion update.
- A restrained property-intelligence visual system: typography, semantic status colour, clear tables/timelines, accessible forms and responsive navigation. No decorative gradients, fake dashboards, or frontend score calculation.

## Testing strategy

- Unit tests: state transition validation; authorization decisions; all score components, 90-day cutoff, no-data handling, clamping, deterministic snapshots/versioning.
- Integration tests: registration/login; IDOR prevention; complaint-to-work-order flow; provider completion; rating uniqueness; score endpoint/history.
- Frontend tests: session handling, role navigation, complaint submission/error state, score display, API error presentation.
- Browser: desktop and mobile primary workflow, console/network review, keyboard and basic accessibility checks.

## Boundaries

- Always: preserve layered dependencies; validate input at HTTP boundaries; scope every data query to the caller's estate; update docs and tests with behaviour.
- Ask first: external service integrations, production hosting, data imports, design changes that change the product thesis.
- Never: allow public self-assignment of privileged roles; calculate scores in React; add AI/ML as MVP theatre; leak raw ORM models; expose development credentials or secrets.

## Success criteria

The acceptance criteria in [VALORA MVP Capability Map](VALORA_MVP_CAPABILITY_MAP.md) are met from a clean startup with migrations, deterministic seed data, automated tests, and browser verification. Documentation accurately describes only verified behaviour.

## Open questions

1. The PRD uses both a five-business-day and one-day resolution benchmark, while the installed Living Score skill specifies one day as 100 and 30 days as zero. This specification adopts the installed skill's concrete one-to-30-day normalization for `v1.0.0` unless you direct otherwise.
2. Existing documentation claims a React frontend was previously approved, but no frontend source exists in this repository. This specification treats the new checked-in frontend as the source of truth.
