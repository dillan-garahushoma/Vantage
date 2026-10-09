# VALORA Implementation Status

**Status date:** 2026-10-09
**Current work:** Phase 0 hardening pass H, Batch F complete
**Migration head:** `d4a7e1c9b3f2`

## Phase 0

The Phase 0 hardening batches are implemented. Batch-level details and actual verification commands are recorded in `docs/progress/phase0-partial.md` and `docs/progress/phase0-{D,E,F}.md`.

| Area | Status |
|---|---|
| Authentication and error contracts | Implemented; malformed, expired, and invalid JWT tests return 401 |
| Estate authorization | Implemented using persisted membership and estate-scoped access |
| Complaint/work-order lifecycle | Implemented, including single-writer resident rating updates |
| Schema constraints | Implemented; offline Alembic generation verified |
| Legacy isolation | Implemented; feature flag defaults off |
| CI and dependency pinning | Implemented; CI runs tests, compileall, offline Alembic generation, and flake8 with pinned constraints |
| Docker Compose | Frontend is profile-gated and configured for the `../frontend` path and port 5173 |

## Not yet verified

- Database-backed integration tests were skipped when `TEST_DATABASE_URL` was absent. Their SQL scoping, locking, and concurrent behavior have not been verified against live PostgreSQL.
- Migrations have not been applied to a live or clean-start database in this pass.
- Browser/frontend verification was not run; this batch does not create a frontend.

The CI test environment explicitly sets `DATABASE_URL`, `SECRET_KEY`, and `CORS_ORIGINS` from the test configuration. `TEST_DATABASE_URL` is intentionally unset in ordinary CI, so database integration tests remain skipped until a disposable test database is provisioned.
