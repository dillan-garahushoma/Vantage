# VALORA — Hardening Pass H: Partial Progress Report

**Date:** 2026-10-08
**Branch:** `valora-work`
**Working Tree Status:** Preserved dirty working tree (no resets, cleanups, commits, or pushes).

---

## 1. Batch Status Summary

| Batch | Description | Status |
|---|---|---|
| **Batch T** | Integration test harness & fixtures | **Done** |
| **Batch A** | Auth hardening, error envelopes, request IDs | **Done** |
| **Batch B** | Dual-role authorization model & tenant scoping | **Done** |
| **Batch C** | Operational flow integrity (work orders & complaints) | **Done** |
| **Batch D** | DB constraints migration & SQLAlchemy model updates | **Done** (offline SQL verified; live DB apply pending) |
| **Batch E** | Legacy route isolation & score class renaming | **Done** |
| **Batch F** | CI, Docker Compose, pinned constraints, ADRs/docs | **Done** (see `phase0-F.md`) |

---

## 2. Details per Batch

### Batch T — Integration Test Harness
- **Status:** **Done**
- **Changes Made:**
  - `backend/tests/conftest.py`: Registered `integration` pytest marker. Configured auto-skip when `TEST_DATABASE_URL` is unset. Implemented hard safety refusal if database name in `TEST_DATABASE_URL` does not contain `test`. Configured session fixture for `alembic upgrade head` and per-test function fixture truncating tables with `TRUNCATE ... RESTART IDENTITY CASCADE`. Configured `httpx.AsyncClient` with `ASGITransport(app=app)` and per-test `NullPool` engine overriding `get_db`.
  - `backend/tests/factories.py`: Implemented `build_two_estate_world` factory provisioning Estate A & Estate B, HOA admins, residents (including resident with two properties in same estate), provider users, and cross-estate resident.
- **Tests Added:**
  - `backend/tests/test_harness_safety.py` (2 tests: auto-skip on unset `TEST_DATABASE_URL`, failure on non-test DB name).
  - `backend/tests/factories.py` (factory module).
- **Commands Actually Ran & Results:**
  - `& .\backend\venv\Scripts\python.exe -m pytest backend/tests/test_harness_safety.py`
    **Result:** `1 passed, 1 skipped in 1.43s` (Exit code 0).

---

### Batch A — Auth, Error Contract, Request IDs
- **Status:** **Done**
- **Changes Made:**
  - `backend/app/identity/api/dependencies.py`: Moved `int(user_id)` parsing inside the guarded `try` block in `get_current_user`. Validated numeric/string `sub` and required `exp` claim. Returns standard 401 envelope on malformed token, missing claims, expired token, invalid signature, or missing user.
  - `backend/app/core/error_handlers.py`: Sanitized `validation_exception_handler` to omit non-serializable objects and sensitive user input (`ctx` and `input` stripped, preventing password echoing). Encoded via `jsonable_encoder`. Replaced Starlette status constants with raw integer literal `422`. Added `X-Request-ID` header injection on all error responses.
  - `backend/app/main.py`: Installed pure ASGI `RequestIdMiddleware` validating regex `^[A-Za-z0-9._-]{1,64}$`, generating UUID fallback, and ensuring `X-Request-ID` presence on all responses (including 500s).
  - `backend/app/identity/schemas/auth.py`: Added 72-byte UTF-8 password limit validator in `RegisterRequest`.
  - `backend/app/identity/services/auth_service.py`: Added constant-time dummy bcrypt verification (`DUMMY_PASSWORD_HASH`) when user is not found during login to mitigate email enumeration timing attacks.
  - `backend/app/core/config.py`: Added production/staging validation for `SECRET_KEY` (rejecting keys < 32 characters or known development placeholders).
- **Tests Added:**
  - `backend/tests/test_batch_a_auth_and_errors.py` (11 tests covering malformed sub, missing sub, expired token, wrong signature, deleted user, password UTF-8 72-byte limit, validation error sanitization without password echo, request ID regex validation, forced 500 header presence, dummy bcrypt verification on missing user, SECRET_KEY config validation).
- **Commands Actually Ran & Results:**
  - `& .\backend\venv\Scripts\python.exe -m pytest backend/tests/test_batch_a_auth_and_errors.py`
    **Result:** `11 passed in 4.75s` (Exit code 0).

---

### Batch B — Authorization Model
- **Status:** **Done**
- **Changes Made:**
  - `backend/app/identity/repositories/estate_membership_repository.py`: Added `list_for_user_and_estate`. Made `get_for_user_and_estate` deterministic with `order_by(membership_id).limit(1)`.
  - `backend/app/identity/services/estate_authorization_service.py`: Added `EstateAccess` dataclass and implemented `resolve_access(actor, estate_id)` enforcing the dual-role rule (`is_estate_admin` requires both global role and estate membership role).
  - `backend/app/community/services/complaint_service.py`: Replaced global `user.role` admin checks with `access.is_estate_admin`. Removed duplicate `require_membership` call in `create_complaint`. Implemented multi-unit resident property verification (`payload.unit_id not in access.property_ids`). Scrubbed `actor_user_id` on complaint events authored by anonymous complaint creator unless viewer is the author. Converted invalid transition errors from 403 to 409 (`ConflictException`).
  - `backend/app/community/services/announcement_service.py`: Replaced global `user.role` checks with `access.is_estate_admin`.
  - `backend/app/community/schemas/complaint.py`: Removed `assigned_to` from `ComplaintStatusUpdate`.
- **Tests Added:**
  - `backend/tests/test_batch_b_authorization.py` (5 tests covering dual-role authorization, multi-unit resident reporting, anonymous event author scrubbing, 409 conflict on invalid transitions, deterministic membership lookup).
  - Updated existing tests: `backend/tests/test_complaint_lifecycle.py`, `backend/tests/test_work_order_authorization.py`.
- **Commands Actually Ran & Results:**
  - `& .\backend\venv\Scripts\python.exe -m pytest backend/tests/test_batch_b_authorization.py`
    **Result:** `5 passed in 4.54s` (Exit code 0).
  - `& .\backend\venv\Scripts\python.exe -m pytest backend/tests/test_complaint_lifecycle.py backend/tests/test_work_order_authorization.py`
    **Result:** `5 passed in 2.82s` (Exit code 0).

---

### Batch C — Operational Flow Integrity
- **Status:** **Done**
- **Changes Made:**
  - `backend/app/community/repositories/work_order_repository.py`: Added `get_active_for_complaint`, `get_by_id_in_estate_for_update`, `get_provider_rating_aggregate`, and `commit: bool = True` parameter.
  - `backend/app/community/repositories/complaint_repository.py`: Added `get_stats_aggregates` using SQL aggregation (`COUNT ... GROUP BY`, average resolution hours calculation), and `commit: bool = True` parameter.
  - `backend/app/community/services/work_order_service.py`:
    - `create_work_order`: Requires complaint status to be `reviewed` (otherwise 409), rejects duplicate active work order (409), verifies provider has `service_provider` estate membership and global role (409), moves complaint to `assigned`, and records assigned event in a single atomic commit.
    - `update_work_order`: Enforces state machine `assigned -> in_progress -> completed`, prevents providers setting `assigned`/`cancelled` (409), rejects re-opening completed work orders (409), forbids skipping `in_progress` (409), transitions complaint status atomically.
    - `rate_work_order`: Locks work order row with `SELECT ... FOR UPDATE`, checks unrated, moves complaint `resolved -> rated`, recomputes `ServiceProvider.avg_rating` (quantized to 0.01) and `total_reviews` atomically.
- **Tests Added:**
  - `backend/tests/test_batch_c_operational_flow.py` (6 tests covering complaint reviewed prerequisite, duplicate active work order rejection, provider membership verification, strict state transition progression, rate work order concurrency lock and aggregate update, complaint stats SQL aggregation).
- **Commands Actually Ran & Results:**
  - `& .\backend\venv\Scripts\python.exe -m pytest backend/tests/test_batch_c_operational_flow.py`
    **Result:** `6 passed in 4.79s` (Exit code 0).

---

### Batch D — DB Constraints Migration & Models
- **Status:** **Done** (offline SQL verified; live database apply remains pending)
- **Changes Made:**
  - `backend/alembic/versions/d4a7e1c9b3f2_hardening_integrity_constraints.py`: Created migration chained from `c3f9a6d4e1b2` with pre-migration online data checks, dropped global `properties.unit_no` unique constraint, added scoped `(estate_id, unit_no)` unique constraint `uq_properties_estate_unit_no`, added partial unique index `uq_properties_legacy_unit_no` where `estate_id IS NULL`, added partial unique index `uq_estate_memberships_user_estate_null_property`, added foreign keys ondelete RESTRICT (`complaints.unit_id`, `maintenance_work_orders.provider_id`, `reviews.user_id`), added partial unique index `uq_active_work_order_per_complaint`, added check constraints on resident rating (1-5) and priority, and symmetrical downgrade.
  - `backend/app/property/models/property.py`: Removed global `unique=True` on `unit_no`, added `uq_properties_estate_unit_no` UniqueConstraint and `uq_properties_legacy_unit_no` Index.
  - `backend/app/identity/models/estate_membership.py`: Added `uq_estate_memberships_user_estate_null_property` Index.
  - `backend/app/community/models/complaint.py`: Added `ForeignKey("properties.unit_id", ondelete="RESTRICT")` and `ck_complaints_priority_allowed` CheckConstraint.
  - `backend/app/community/models/maintenance_work_order.py`: Added `ForeignKey("service_providers.provider_id", ondelete="RESTRICT")`, `uq_active_work_order_per_complaint` Index, and `ck_work_orders_resident_rating_1_to_5` CheckConstraint.
  - `backend/app/providers/models/review.py`: Added `ForeignKey("users.user_id", ondelete="RESTRICT")`.
  - `backend/app/property/repositories/property_repository.py`: Added `get_by_unit_no_in_estate`.
  - `backend/app/property/services/property_service.py`: Scoped property creation conflict check to `get_by_unit_no_in_estate`.
- **Tests Added:**
  - `backend/tests/test_batch_d_integrity.py` (5 tests verifying all model constraints, foreign keys, indexes, check constraints, and repo methods).
- **Commands Actually Ran & Results:**
  - `& .\backend\venv\Scripts\python.exe -m pytest backend/tests/test_batch_d_integrity.py`
    **Result:** `5 passed in 8.81s` (Exit code 0).
  - `& .\backend\venv\Scripts\python.exe -m pytest backend/tests` (Full suite run)
    **Result:** `37 passed, 1 skipped in 10.49s` (Exit code 0).
- **Verification:** Offline Alembic SQL generation across the full chain is recorded in `phase0-D.md`.
- **Not run:** Live PostgreSQL migration application and data checks.

---

### Batch E — Legacy Route Isolation & Score Class Renaming
- **Status:** **Done**. Legacy routes are gated by default; provider reads are restricted; legacy score types are explicitly named and the endpoint is deprecated.
- **Verification:** See `phase0-E.md` for the five passing tests and the behavior fixed during verification.

---

### Batch F — CI, Compose, Dependencies, Docs
- **Status:** **Done**. CI coverage, profile-gated Compose frontend, pinned backend constraints, ADRs, and implementation status/roadmap updates are complete.
- **Verification and provenance:** See `phase0-F.md` for exact commands and results, the `httpx2` PyPI provenance check, deviations, and remaining live database gates.

---

## 3. Git Status & Diff Summary (Recorded at Stop)

### `git status`
```
On branch valora-work
Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   Guide
	modified:   backend/app/community/models/complaint.py
	modified:   backend/app/community/models/maintenance_work_order.py
	modified:   backend/app/community/repositories/complaint_repository.py
	modified:   backend/app/community/repositories/work_order_repository.py
	modified:   backend/app/community/schemas/complaint.py
	modified:   backend/app/community/services/announcement_service.py
	modified:   backend/app/community/services/complaint_service.py
	modified:   backend/app/community/services/work_order_service.py
	modified:   backend/app/core/config.py
	modified:   backend/app/core/error_handlers.py
	modified:   backend/app/identity/api/dependencies.py
	modified:   backend/app/identity/models/estate_membership.py
	modified:   backend/app/identity/repositories/estate_membership_repository.py
	modified:   backend/app/identity/schemas/auth.py
	modified:   backend/app/identity/services/auth_service.py
	modified:   backend/app/identity/services/estate_authorization_service.py
	modified:   backend/app/main.py
	modified:   backend/app/property/models/property.py
	modified:   backend/app/property/repositories/property_repository.py
	modified:   backend/app/property/services/property_service.py
	modified:   backend/app/providers/models/review.py
	modified:   backend/tests/conftest.py
	modified:   backend/tests/test_complaint_lifecycle.py
	modified:   backend/tests/test_work_order_authorization.py
	modified:   docs/VALORA_PRD.md
	modified:   scratch/generate_doc.py

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	backend/alembic/versions/d4a7e1c9b3f2_hardening_integrity_constraints.py
	backend/tests/factories.py
	backend/tests/test_batch_a_auth_and_errors.py
	backend/tests/test_batch_b_authorization.py
	backend/tests/test_batch_c_operational_flow.py
	backend/tests/test_batch_d_integrity.py
	backend/tests/test_harness_safety.py
```

### `git diff --stat`
```
 Guide                                              |  92 ++++----
 backend/app/community/models/complaint.py          |  10 +-
 backend/app/community/models/maintenance_work_order.py |  16 +-
 backend/app/community/repositories/complaint_repository.py |  82 ++++++-
 backend/app/community/repositories/work_order_repository.py  |  60 ++++-
 backend/app/community/schemas/complaint.py         |   1 -
 backend/app/community/services/announcement_service.py |   8 +-
 backend/app/community/services/complaint_service.py    | 123 +++-------
 backend/app/community/services/work_order_service.py   | 248 ++++++++++++++++-----
 backend/app/core/config.py                         |  17 ++
 backend/app/core/error_handlers.py                 |  45 +++-
 backend/app/identity/api/dependencies.py           |  15 +-
 backend/app/identity/models/estate_membership.py   |   9 +-
 backend/app/identity/repositories/estate_membership_repository.py |  20 +-
 backend/app/identity/schemas/auth.py               |   9 +-
 backend/app/identity/services/auth_service.py      |  10 +-
 backend/app/identity/services/estate_authorization_service.py |  84 ++++++-
 backend/app/main.py                                |  54 ++++-
 backend/app/property/models/property.py            |  13 +-
 backend/app/property/repositories/property_repository.py |  12 +
 backend/app/property/services/property_service.py  |   4 +-
 backend/app/providers/models/review.py             |   2 +-
 backend/tests/conftest.py                          | 101 +++++++++
 backend/tests/test_complaint_lifecycle.py          |  23 +-
 backend/tests/test_work_order_authorization.py     |   8 +-
 docs/VALORA_PRD.md                                 |   2 +-
 scratch/generate_doc.py                            |   2 +-
 27 files changed, 798 insertions(+), 272 deletions(-)
```
