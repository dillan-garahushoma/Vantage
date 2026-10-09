# VALORA Execution Roadmap

## Current checkpoint: Phase 0 hardening

The implementation work for Phase 0 Batches T and A–F is recorded in `docs/progress/phase0-*.md`. The current Alembic migration head is **`d4a7e1c9b3f2`**.

| Batch | Scope | Status |
|---|---|---|
| T | Integration harness and shared estate-world factory | Complete; live DB execution remains pending |
| A | Authentication, standardized errors, request IDs | Complete |
| B | Estate authorization and tenant scoping | Complete |
| C | Complaint and work-order lifecycle integrity | Complete |
| D | Integrity constraints and migration | Offline SQL verified; live DB apply pending |
| E | Legacy route isolation and score naming | Complete |
| F | CI, Compose, pinned constraints, ADRs and status docs | Complete |

## Remaining Phase 0 acceptance

- Run the integration suite against a disposable PostgreSQL database whose name contains `test`.
- Apply the full migration chain to an empty PostgreSQL database and verify the resulting schema and data checks.
- Review the feature and operational reports in `docs/progress/` before opening Phase 1 work.

## Subsequent work

Phase 1 and later product capabilities remain outside this hardening pass. Do not treat roadmap descriptions in older planning documents as authorization to begin those tasks; continue only after the Phase 0 handoff is accepted.
