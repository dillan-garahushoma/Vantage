# Implementation Plan: VALORA Core Operational Intelligence MVP

## Overview

Deliver the approved estate-scoped operational intelligence loop in thin vertical slices. The migration and authorization foundation comes first; all subsequent backend and frontend work depends on it. The plan keeps legacy listings and AI-analytic scaffolding untouched unless an isolated compatibility issue requires removal from the active API.

## Architecture decisions

- Evolve the existing modular FastAPI monolith instead of replacing it. Routers remain thin; services own workflow transitions; repositories own query/persistence work.
- Introduce `Estate` and membership as the tenant/authorization boundary. Existing property records remain the property/unit aggregate to avoid duplicate entities.
- Use append-only events and snapshots for historical operational signals. Mutable current state remains on complaint/work-order rows for simple querying.
- Use an estate-level deterministic Living Score `v1.0.0`, rather than the existing property-only score.
- Build a Vite React application in `frontend/` with a typed API client and no frontend business rules.

## Delivery sequence

1. Establish test tooling and security-safe configuration.
2. Add estate tenancy, memberships, and property context migration/contract.
3. Make authentication and authorization estate-aware.
4. Build complaint event lifecycle and HOA review endpoint.
5. Build provider account linkage, work-order assignment/progress, and rating flow.
6. Add security incidents and Living Score calculations/snapshots/history.
7. Add deterministic seed data and integration tests for the core backend journey.
8. Build the frontend shell, authentication, and public screens.
9. Build resident, HOA, and provider product flows against the real API.
10. Run browser, security, performance, code-review, and documentation quality gates.

## Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Existing database has no estate keys | High | Use an additive migration with nullable backfill strategy for legacy data; seed only after migration. |
| Current authentication permits role escalation | High | Restrict public registration before exposing new endpoints; cover it with API tests. |
| Docker daemon is unavailable locally | Medium | Validate code and client builds locally where possible; document Docker verification as pending if daemon remains unavailable. |
| Frontend has no base tooling | Medium | Use a small Vite/React dependency surface and committed lockfile. |
| Historical score requirement is easy to fake | High | Implement and test persisted snapshots, version string, cut-off filtering, and repeatable calculations. |

## Quality checkpoints

- Foundation: migration and authorization tests pass before operational endpoints are added.
- Backend vertical slice: seeded resident/HOA/provider workflow passes integration tests.
- Frontend vertical slice: browser journey has no console/network errors at desktop and mobile widths.
- Release gate: security, performance, documentation, and code review findings are resolved or recorded.
