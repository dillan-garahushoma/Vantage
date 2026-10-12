# ONB-1 — Role-scoped onboarding and operator role

Batch: ONB-1 (role-aware signup, estate registration, re-scoping of role-only
endpoints). Status: **implemented and verified** except for the integration path
that needs a live PostgreSQL (`TEST_DATABASE_URL` unset in this session).

Related docs: [ADR-006](../ADR-006-role-scoped-onboarding.md) (supersedes the
resident-only registration clause of ADR-002 and the global-role-only provider
write gate).

## What changed

### PART A — close the global-role-only blast radius

| Endpoint | Old gate | Estate-scoped? | What a self-registered `hoa_admin` could have done | Now |
|---|---|---|---|---|
| `POST /api/v1/providers` | global `hoa_admin` | no | Create a provider anywhere with no estate tie-in | `platform_admin` only (403 otherwise) |
| `PATCH /api/v1/providers/{id}` (incl. `verified`) | global `hoa_admin` | no | Flip a provider's `verified` trust flag | `platform_admin` only |
| `POST /api/v1/listings` | global `estate_agent`/`hoa_admin` | no | List a unit in a **foreign** estate, or a legacy `estate_id IS NULL` unit | global role **and** `hoa_admin` membership in the unit's estate; legacy `NULL` denied |
| `PATCH /api/v1/listings/{id}` | global `estate_agent`/`hoa_admin` | no | Edit another estate's listing | same membership rule; `estate_agent` ownership rule unchanged |
| `POST /api/v1/sales` | global `estate_agent`/`hoa_admin` | no | Record a sale against a foreign-estate unit | global role **and** `hoa_admin` membership in the unit's estate |
| complaints / announcements / incidents / work-orders | global `hoa_admin` (±`resident`) | **yes** | nothing beyond own estate | already resolved membership via `EstateAuthorizationService.resolve_access`; unchanged |
| living-score / health-brief (analytics) | global `hoa_admin` | **yes** | nothing beyond own estate | already scoped via `require_membership` / `require_role` (both credential halves); unchanged |

`platform_admin` was added to `app.common.enums.UserRole`. The `role` column is
`String(20)`, so no migration was needed and none was added.

New operator CLI `backend/scripts/assign_platform_admin.py`: dry-run by default,
prints the redacted target `host:port/database`, refuses a demo-looking database
unless `--allow-demo-database`, supports `--expect-database NAME`, is idempotent,
and reads `DATABASE_URL` from the environment only (never `.env`).

### PART B — role-scoped public signup

`RegisterRequest` (in `app/identity/schemas/auth.py`) now takes
`account_type` ∈ {`resident` (default), `estate_admin`, `service_provider`}, plus
an `estate` object (`estate_admin`) or `provider` object (`service_provider`). A
`role` field is still rejected, and non-selectable types (`platform_admin`,
`estate_agent`, `investor`) are rejected. Cross-field validation enforces the
matching payload.

`AuthService.register` dispatches:
- `estate_admin` → user (`hoa_admin`) + non-demo estate + estate-level membership
  (`hoa_admin`, no property), **committed once**. Duplicate estate name → 409 with
  no orphan user.
- `service_provider` → user (`service_provider`) + linked provider profile
  (`verified=false`, no membership), **committed once**.
- `resident` → the original single-row path.

Repositories used by these multi-step paths (`add`) only `flush`; the service owns
the single commit, per the architecture rule.

## Tests added and passing

`backend/tests/test_onb1_role_scoped_signup.py` — 48 tests (33 policy/DTO/service
tests run everywhere; 15 `@pytest.mark.integration` carry the DB-backed claims and
skip without `TEST_DATABASE_URL`). Coverage: `role`/unknown/non-selectable
`account_type` rejection, required estate/provider payloads, resident payload
purity, provider writes denied for every non-platform role and allowed for
`platform_admin`, listing/sale cross-estate and legacy-NULL denials, in-estate
success, unchanged `estate_agent` behaviour, one-transaction estate signup with
rollback and duplicate-name 409, provider signup linking a profile with zero
estate access, `platform_admin` unobtainable via any public endpoint, no password
in logs, and the operator CLI's dry-run/apply/missing-account/demo-db/`.env`/
redaction behaviour.

## Deviations

- No migration: `role` is already `String(20)`, so the new enum member needs none.
- An ADR describing the decision did not exist in the tree; ADR-006 was written to
  record it (the batch asked for a superseding ADR).

## Commands run and results (this session)

| Command | Result |
|---|---|
| `venv\Scripts\python.exe -m pytest tests/test_onb1_role_scoped_signup.py -q` | **33 passed, 15 skipped** |
| `venv\Scripts\python.exe -m pytest tests -q` | **642 passed, 78 skipped, 5 failed** |
| `venv\Scripts\python.exe -m compileall -q app` | OK |
| `venv\Scripts\python.exe -m flake8 app tests --count --select=E9,F63,F7,F82 --show-source --statistics` | **0** |
| `venv\Scripts\python.exe -m alembic -c alembic.ini heads` | `d9f2a4c7e1b3 (head)` (single head) |
| `git diff --check` | clean (exit 0) |
| `python -m app.cli export-openapi` | regenerated `docs/openapi.json`; `RegisterRequest` now publishes `account_type`, `estate`, `provider` |
| `pytest tests/test_batch_a_pagination_contract.py tests/test_batch_e_legacy_isolation.py -q` | **10 passed** (both read the committed `docs/openapi.json`; confirms the regenerated file stays consistent) |
| `pytest tests/test_vocabulary_openapi_contract.py -q` | passed (part of the 39-passed run above) |

## Written but not run

- Integration tests (15) — require `TEST_DATABASE_URL` pointing at a `*test*`
  database. Not set in this session, so they **skipped**; a skip is not a pass.
- Applying migrations / a clean-start run against live PostgreSQL — not available
  on this workstation.

## Pre-existing failures (not caused by ONB-1)

`tests/test_ai_guard.py` (4) and `tests/test_ai_pilot_report.py` (1) fail
(`DID NOT RAISE AIUnavailableError`; a `since`-window bound assert). These are
AI-batch tests unrelated to onboarding; they were failing independently of these
changes and were left untouched.

## Open questions

1. Should `estate_agent` and `investor` become self-selectable account types, and
   if so what estate/provider proof should they carry?
2. Provider estate access is "provisioned separately" — the concrete operator
   path for binding a provider to an estate is not built yet.
3. `platform_admin` has no revoke path or audit trail beyond the CLI output.
