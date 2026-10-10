# Phase 0 — Batch E: Legacy isolation

## Result

Batch E is implemented. Legacy listings, sales, provider review endpoints, and provider write endpoints are gated behind `ENABLE_LEGACY_ROUTES`, which defaults to false. Provider listing and profile reads enforce the membership/self-access rules. Legacy score symbols are now named `LegacyPropertyScore*`, and the legacy score endpoint is marked deprecated.

## Verification

From `backend`:

```powershell
& .\venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\test_batch_e_legacy_isolation.py -q
```

Result: `5 passed in 8.48s`.

The test covers routes missing from OpenAPI and returning 404 when disabled, route behavior when enabled, provider membership/self-read authorization, and legacy score naming/deprecation by source references.

During verification, disabled provider `POST` and `PATCH` methods initially returned 405 because corresponding `GET` paths still exist. Hidden fallback routes now return 404 without appearing in OpenAPI, matching the required disabled-route contract. The enabled provider-create test uses a syntactically valid test email; the review-creation request uses a resident identity as required by the existing role dependency.

## Paths changed for this batch

- `backend/app/core/config.py`
- `backend/app/api/router.py`
- `backend/app/property/api/router.py`
- `backend/app/providers/api/router.py`
- `backend/app/providers/services/service_provider_service.py`
- `backend/app/providers/repositories/service_provider_repository.py`
- `backend/app/property/api/properties.py`
- `backend/app/analytics/domain/entities.py`
- `backend/app/analytics/repositories/living_score_repository.py`
- `backend/app/analytics/schemas/living_score.py`
- `backend/app/analytics/services/living_score_service.py`
- `backend/tests/test_batch_e_legacy_isolation.py`
- `docs/progress/phase0-E.md`

## Not run / remaining

- Full backend suite and live PostgreSQL tests were not run for this batch.
- No commits were created. Batch F remains.
