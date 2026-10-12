# Group8 Project → VANTAGE Reconciliation

**Date:** 2026-10-10
**Destination (preserved):** VANTAGE — branch `valora-work`
**Source (read-only):** Group8Project — branch `main`
**Author:** Buffy (Codebuff), acting under the VALORA agent instructions.

This report records the baseline, the module-by-module comparison, the work
actually integrated, the checks that were actually run, and a prioritized
backlog. Statements are labelled "ran" or "written, not run" per the honesty
rule.

---

## 1. Repository baselines

| Item | VANTAGE (destination) | Group8Project (source) |
|---|---|---|
| Root path | `C:\Users\garah\PycharmProjects\VANTAGE` | `C:\Users\garah\PycharmProjects\Group8Project` |
| Backend path | `backend/` | `Group8Project-main/backend/` (a nested copy also exists at top-level `backend/` and `backend_old/`) |
| Branch | `valora-work` | `main` |
| Commit | `0849c05c8bf489989d38695327753c96aae9dd1c` | `807e617ee1ad2d316237e318025d18dcede59fb0` |
| Working tree | clean except untracked `.freebuff/` and `test_batch_a_out.txt` (pre-existing, left untouched) | only `__pycache__/*.pyc` churn (96 files) |
| Alembic head | `d4a7e1c9b3f2` (single head; 6 revisions) | `103dd39ca30e` (2 revisions: `5c5c0e0ef686`, `103dd39ca30e`) |
| Tests | 15 files → **52 passed, 1 skipped** (baseline) | no collected test suite in the backend tree |
| Virtualenv | `backend/venv/` | `backend/venv/` and `Group8Project-main/backend/venv/` (not copied) |

No production database was connected to. No secrets were read or printed.

### Security finding (report only — no values printed)

`Group8Project-main/backend/.env` is **tracked by Git**, even though
`Group8Project-main/backend/.gitignore` lists `.env`. A committed environment
file is a credential-disclosure risk. Recommended, outside this task:

- Rotate every credential the file may have contained (`DATABASE_URL`
  password, `SECRET_KEY`, any provider keys).
- Untrack it without deleting the working copy: `git rm --cached <path>` and
  rely on `.gitignore`; scrub history only with a reviewed, coordinated
  rewrite.
- Do not copy the file (or any venv) into VANTAGE. **It was not copied.**

Separately, `Group8Project-main/backend/app/api/users.py` hardcodes
`SECRET_KEY = "your-secret-key"`. That module is a legacy artifact and was
**not** copied.

---

## 2. Comparison matrix and decisions

Group8Project is an **earlier snapshot of the same project** as VANTAGE, plus a
handful of unwired "Kai" scaffolding modules. Every layered module it shares
with VANTAGE exists in VANTAGE in a strictly more hardened form (estate-scoped
authorization, standardized error envelopes, integrity constraints). The
registered route set in VANTAGE is a strict superset of Group8's.

Classification key: **KEEP VANTAGE** · **PORT** · **MERGE** · **FIX ON
INTEGRATION** · **INVESTIGATE** · **DEFER**.

| Capability | Group8 | VANTAGE | Decision |
|---|---|---|---|
| Auth (register/login/me, JWT) | async, no rate limiting | async + dummy-bcrypt timing defence, 401 envelopes | **KEEP VANTAGE**; **FIX ON INTEGRATION** for login-attempt tracking (below) |
| Login-attempt tracking | `core/login_attempts_kai.py` — unregistered, flat imports, unauthenticated CRUD | model + `login_attempts` table, no service/API | **FIX ON INTEGRATION** (implemented — §3) |
| Sessions / logout | `core/sessions_kai.py` — unregistered, trusts client `user_id` | model + `sessions` table, no service/API | **DEFER** (needs a product decision on JWT-only vs refresh tokens — §8) |
| User management endpoints | `api/users.py` — unregistered, hardcoded secret, lists all users unauthenticated | `/auth/me` only | **DEFER** as operator tooling (§8); never re-enable the insecure version |
| Estates / memberships / tenancy | estate-scoping absent | `Estate`, `EstateMembership`, `EstateAuthorizationService.resolve_access`, estate-scoped repos | **KEEP VANTAGE** |
| Properties | unscoped `get_property(unit_id)` | estate-scoped `get_property(unit_id, estate_id, actor)`; scoped `unit_no` uniqueness | **KEEP VANTAGE** |
| Listings | present | present (legacy-gated by `ENABLE_LEGACY_ROUTES`) | **KEEP VANTAGE** |
| Sales | `sales_service.py` **broken** (`list_sales` calls `search_sales`; `create_sale(payload)` vs `create_sale(payload, agent)`) | working `sale_service.py` matching its router | **KEEP VANTAGE** (VANTAGE is the fix) |
| Complaints + lifecycle | no complaint-event history | `complaint_event.py`, `/complaints/{id}/events`, atomic transitions, 409 on invalid | **KEEP VANTAGE** |
| Work orders + rating | present | strict state machine, `SELECT … FOR UPDATE`, provider aggregate recompute | **KEEP VANTAGE** |
| Announcements | present | `resolve_access`, expired-hidden for non-admins | **KEEP VANTAGE** |
| Service providers + reviews | provider routes ungated | provider writes gated behind `ENABLE_LEGACY_ROUTES`; membership checks | **KEEP VANTAGE** |
| Living Score (40/30/30) | `LivingScoreService` exposed at `/{unit_id}/living-score` | **identical formula**, renamed `LegacyPropertyScoreService`/`LegacyPropertyScoreRepository`/`LegacyPropertyScoreResponse`, route `deprecated=True`, estate-authorized | **KEEP VANTAGE** (same logic, isolated as legacy) |
| Analytics / AI analytics | `analytics/api/ai_analytics_kai.py` — unregistered CRUD over `AIAnalytic` | `/analytics/status` only; `AIAnalytic` model exists | **DEFER** (post-MVP — §8) |
| Contact | present (with typo `contact/init.py`) | present (correct `contact/__init__.py`) | **KEEP VANTAGE** |
| Error contract / request IDs | absent | `core/error_handlers.py`, `X-Request-ID` middleware | **KEEP VANTAGE** |
| Pagination envelope | absent | `common/pagination.py` `Page[T]`, `PaginationParams` | **KEEP VANTAGE** |
| DB integrity constraints | absent | `d4a7e1c9b3f2` (scoped uniqueness, FKs RESTRICT, check constraints, partial unique active-WO index) | **KEEP VANTAGE** |
| Migrations | 2 revisions, different lineage | 6 revisions, additive lineage | **KEEP VANTAGE** (do not merge histories) |
| Dead code in Group8 | `community/repositories/complaint_respository.py` (typo), `contact/init.py` (typo) | — | **IGNORE** |

**Net result:** Group8 contains **no wired, working functionality that VANTAGE
lacks**. Its unique modules are unregistered and, in the case of imports, do not
even resolve (`from app.database import …`, `from app.models import …` refer to
a flat structure that no longer exists). The only defensible integration is to
promote the *intent* of the login-attempt module into VANTAGE's architecture,
which is the one team capability that maps cleanly onto an existing VANTAGE
table and a clear security requirement.

---

## 3. Team functionality successfully incorporated

### Login-attempt tracking + per-account rate limiting (fix-on-integration)

The team's `core/login_attempts_kai.py` recorded attempts and exposed a
`check-rate-limit` query (5 failures / 15 minutes). That intent was **adapted**
into VANTAGE's async layered architecture and made secure:

- New `backend/app/identity/repositories/login_attempt_repository.py`
  (`record`, `count_recent_failures`) — flush only, service commits.
- New `RateLimitException` (429) in `backend/app/core/exceptions.py`; the
  existing error handler already maps 429 → `RATE_LIMITED`.
- `backend/app/core/config.py`: `LOGIN_MAX_FAILED_ATTEMPTS=5`,
  `LOGIN_LOCKOUT_WINDOW_MINUTES=15`.
- `backend/app/identity/services/auth_service.py`: `login()` now enforces the
  failure window **before** credential verification, records every attempt
  (success and failure) with client IP, and commits once. Dummy-bcrypt timing
  defence is preserved.
- `backend/app/identity/api/router.py`: `POST /api/v1/auth/login` passes the
  client IP from the ASGI request; keeps the response contract unchanged.

Deliberately **not** ported: the team's unauthenticated `GET/POST/DELETE
/api/login-attempts*` endpoints. Those are operator tooling and would need an
authorization design (§8).

---

## 4. VANTAGE functionality preserved

Everything VANTAGE already had was preserved. No VANTAGE file was replaced with
a Group8 version. No behaviour or response contract was changed: the login
success/failure responses are byte-identical for the existing happy and
invalid-credential paths; a new 429 is added only for the abuse case.

No destructive Git command was run. No commit, push, or deploy was performed.
The pre-existing untracked `.freebuff/` and `test_batch_a_out.txt` were left
untouched.

---

## 5. Files changed (with reasons)

| File | Change | Reason |
|---|---|---|
| `backend/app/identity/repositories/login_attempt_repository.py` | **new** | Persistence for attempts; ports the team's intent into a repository |
| `backend/app/core/exceptions.py` | added `RateLimitException` | Needed a 429 with the standard envelope |
| `backend/app/core/config.py` | added 2 settings | Make thresholds configurable instead of hardcoded |
| `backend/app/identity/services/auth_service.py` | integrate enforcement + recording | Business rule lives in the service, not the router |
| `backend/app/identity/api/router.py` | pass client IP | Keeps router thin; supplies audit data |
| `backend/app/identity/api/…` (none other) | — | — |
| `backend/tests/test_login_rate_limit.py` | **new** (4 tests) | Cover lockout, failure recording, success recording, 429 envelope |
| `backend/tests/test_batch_a_auth_and_errors.py` | updated one test's fakes | The service gained dependencies; assertions unchanged (not weakened) |

---

## 6. Database and migration decisions

- Login-attempt tracking reuses the **existing** `login_attempts` table
  (created by `5c5c0e0ef686_consolidated_architecture`) and the existing
  `LoginAttempts` ORM model. **No migration was added or run.**
- The team's migration lineage was **not** merged. VANTAGE keeps its own head
  `d4a7e1c9b3f2`. `alembic heads` reports a single head (ran).
- The integration writes only to a table that already exists, so no schema
  change is required and no live database was touched.

---

## 7. Commands actually run and results

From `VANTAGE/backend`, unless noted. Interpreter: `backend/venv/Scripts/python.exe`.

| Command | Result |
|---|---|
| `python -m pytest tests -q -p no:cacheprovider` (baseline) | **52 passed, 1 skipped** |
| `python -m pytest tests/test_login_rate_limit.py tests/test_batch_a_auth_and_errors.py -q` | **15 passed** |
| `python -m pytest tests -q -p no:cacheprovider` (after change) | **56 passed, 1 skipped** |
| `python -m compileall -q app` | exit 0 |
| `python -m flake8 app tests --count --select=E9,F63,F7,F82` | `0` |
| `git diff --check` | clean |
| `alembic -c alembic.ini heads` (with `DATABASE_URL`/`SECRET_KEY` set) | `d4a7e1c9b3f2 (head)` |

**The 1 skip is an integration test skipped because `TEST_DATABASE_URL` is not
set in this terminal.** It is *not* counted as a pass. The DB-backed
authorization/lifecycle tests therefore ran against their fake-session stubs,
not PostgreSQL, in this session. Live-DB verification of the new rate-limit
path remains outstanding (§8).

**Written, not run:** nothing in this integration is unexecuted except the
PostgreSQL-backed integration path, as noted.

---

## 8. Remaining compatibility issues, unresolved decisions, unverified

1. **Living Score formula conflict — RESOLVED 2026-10-10 by product-owner
   decision (see `docs/ADR-005-Living-Score-Authority.md`).** The finding as
   recorded at the time: the team's 40/30/30 engine is *already inside VANTAGE*
   as the legacy property-score service. VANTAGE's docs propose a five-component
   formula (adding security + satisfaction). These are different authorities.
   Until the product owner confirmed which was authoritative, the five-component
   formula was **not** implemented and the legacy route stayed legacy. No
   blending was performed.

   **Resolution:** the five-component, estate-level Living Score `v1.0.0`
   (0.30 resolution / 0.25 frequency / 0.20 security / 0.15 satisfaction / 0.10
   infrastructure, rolling 90-day window, immutable `LivingScoreSnapshot` with
   `engine_version`) is authoritative. The legacy 40/30/30 per-property score is
   **not** Living Score v1: it stays isolated as `LegacyPropertyScore*` under
   ADR-003 and must not be extended, re-weighted, presented as Living Score, or
   used to backfill a snapshot. This matches `docs/SPEC-VALORA-MVP-CORE.md`,
   which already called for the legacy score to be superseded.

   **What the resolution does not do:** no code, migration, model, endpoint or
   test was changed. The estate snapshot engine, the 90-day calculation and the
   history API are still unbuilt (Task 7), so the AI Health Brief (BATCH AI-4)
   remains blocked — now only by the missing implementation, not by a product
   question. Security incidents are still absent (Task 6), so the Security
   sub-score has no input yet.
2. **Session / logout semantics (decision needed).** The `sessions` table and
   `Session` model exist but there is no service/API. The frontend contract is
   JWT-only. Adding opaque refresh tokens is a product decision (complement or
   replace the access token). Deferred.
3. **User management / operator tooling (decision needed).** No admin
   user-list endpoint exists (correctly — the team's version was
   unauthenticated). Building it needs an authorization design (platform
   operator vs estate admin).
4. **Login-attempt integration not exercised against PostgreSQL** in this
   terminal (`TEST_DATABASE_URL` unset). The 429/record/commit paths are unit
   tested with fakes; a live-DB smoke test is required before pilot.
5. **Request-scoped IP behind a proxy** — `request.client.host` reflects the
   direct peer. If deployed behind a proxy, a trusted `Forwarded`/`X-Forwarded-For`
   policy is required; not implemented.
6. **`AIAnalytic` model is unused** (no API in either repo). Left as-is.

---

## 9. Prioritized backlog (verified against the actual code)

Nothing below was implemented; each was checked against the code before listing.

### MVP blockers
- **Estate read API.** `Estate` + `EstateMembership` + `EstateAuthorizationService`
  exist and are estate-scoped everywhere, but there is **no** `/estates` router
  (verified: no route registered). Residents/HOAs need estate discovery/reads.
- **Invitations & onboarding.** No invitation/onboarding code exists (verified:
  zero matches). Registration creates residents only; there is no way to grant
  HOA/provider capabilities with the required **both-global-role-and-membership**
  rule.
- **Living Score persistence + decision.** Scores are computed on the fly and
  not stored; no history table. The formula decision is **resolved** (§8.1,
  ADR-005: five-component estate-level `v1.0.0`); what remains is the
  implementation — Task 7's snapshot model, 90-day calculation and history API.

### Pilot-readiness
- **Session & logout** (needs the §8.2 decision).
- **Login-attempt operator visibility** — recording exists, but no authorized
  read endpoint to surface incidents.
- **Security-incident / operator tooling** — absent (verified: zero matches).
- **Provider provisioning** — provider create/update exist but are gated behind
  `ENABLE_LEGACY_ROUTES=True`; onboarding a real provider through the modern
  path is not the default.
- **Live-DB integration pass** with `TEST_DATABASE_URL` set (turn the skip into
  a pass or a documented failure).

### Post-MVP
- **AI analytics API** over `AIAnalytic` (the team's unregistered CRUD is a
  starting shape, not a design).
- **Advanced ML / predictive valuation** (`ValuationResult` domain entity
  exists; no service).

---

## 10. Recommended implementation sequence

1. ~~**Resolve the Living Score authority** (product decision)~~ — **done
   2026-10-10**; the five-component estate-level `v1.0.0` score governs
   (ADR-005). The next step is implementing it (Task 7), which was previously
   gated on this decision and must not be guessed at in code.
2. **Estate read API** in VANTAGE's layered style, reusing
   `EstateRepository`/`EstateAuthorizationService`.
3. **Invitations & onboarding** with the dual-role rule and tests.
4. **Session/logout** once the token-model decision is made.
5. **Operator tooling** (login-attempt reads, security incidents) with an
   explicit authorization model.
6. **Provider provisioning** on the modern (non-legacy) path.
7. **Live-DB verification pass** after each of the above.

---

## Appendix — Integration summary

- **Integrated:** login-attempt tracking + per-account rate limiting (adapted
  from `login_attempts_kai`, made secure, wired into `AuthService.login`).
- **Preserved:** all VANTAGE architecture, security, contracts, tests, and
  migrations.
- **Rejected:** Group8 `.env`, venvs, dead/typo modules, the insecure
  `api/users.py`, the broken `sales_service.py`, and the team's migration
  lineage.
- **Deferred with documented decisions:** sessions, user-management/operator
  tooling, AI analytics, and the Living Score formula.
