# Phase 1 — Batch A: API contract alignment

## Final status

Batch A is complete in the current worktree and verified against the backend suite with `TEST_DATABASE_URL` set.

## What was done

- Added a shared generic `Page[T]` and `PaginationParams` in [backend/app/common/pagination.py](C:/Users/garah/PycharmProjects/VANTAGE/backend/app/common/pagination.py).
- Migrated the non-legacy list endpoints to the standard envelope `{items, total, page, size, pages}` for complaints, work orders, announcements, properties, and providers in:
  - [backend/app/community/api/complaints.py](C:/Users/garah/PycharmProjects/VANTAGE/backend/app/community/api/complaints.py)
  - [backend/app/community/api/work_orders.py](C:/Users/garah/PycharmProjects/VANTAGE/backend/app/community/api/work_orders.py)
  - [backend/app/community/api/announcements.py](C:/Users/garah/PycharmProjects/VANTAGE/backend/app/community/api/announcements.py)
  - [backend/app/property/api/properties.py](C:/Users/garah/PycharmProjects/VANTAGE/backend/app/property/api/properties.py)
  - [backend/app/providers/api/router.py](C:/Users/garah/PycharmProjects/VANTAGE/backend/app/providers/api/router.py)
- Added allow-listed sort validation for complaint and work-order list endpoints, with invalid values yielding 422.
- Preserved stable operation IDs via the FastAPI app config in [backend/app/main.py](C:/Users/garah/PycharmProjects/VANTAGE/backend/app/main.py).
- Added/updated contract coverage in [backend/tests/test_batch_a_pagination_contract.py](C:/Users/garah/PycharmProjects/VANTAGE/backend/tests/test_batch_a_pagination_contract.py).
- Updated response schemas to serialize by alias where required while leaving the contract strict: only the resource’s own id alias is emitted, not legacy foreign-key names.

## Batch A six-item status

1. Page envelope on all non-legacy lists — Done
2. Sort allow-lists — Done
3. Operation IDs — Done
4. OpenAPI export plus CI check — Done (export path and deterministic generation are in place; CI diff gate is present in the project workflow)
5. Contract tests — Done
6. Updated old tests — Done

## Verification

From the backend directory, with `TEST_DATABASE_URL` set:

```powershell
Set-Location 'C:\Users\garah\PycharmProjects\VANTAGE\backend'
$env:TEST_DATABASE_URL='postgresql+asyncpg://postgres:postgres@localhost:5432/vantage_test'
.\venv\Scripts\python -m pytest -q -p no:cacheprovider
```

Result: **53 passed, 3 warnings**.

The warnings are deprecation warnings from FastAPI startup hooks and the `httpx`-based test client, not contract failures.

## Notes

- The earlier auth discrepancy was confirmed as expected FastAPI behavior: unauthenticated requests raise 401 before query validation can report 422.
- The legacy-id issue was resolved by strict alias handling in the response schema and the tests’ per-resource identifier assertions, not by weakening the contract.
- No commit was created during this batch.
