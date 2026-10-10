> **SESSION TASK: execute ONLY Batch E2.** Do not start any other batch. Follow the session protocol below.

# VALORA — Phase 1: Domain Foundation (Task 6 expanded)

## 0. Context, preconditions, precedence

Phase 0 (the Hardening Pass H) must be complete and its report approved before you start. This prompt assumes its outcomes. **Check these first and stop with a report if any is missing:**

1. `EstateAccess` / `resolve_access` exists in `EstateAuthorizationService`, and services use it (not the global `user.role`) for admin/provider/resident decisions.
2. The integration test harness exists (`integration` marker, `TEST_DATABASE_URL`, two-estate factories).
3. The legacy-routes flag `ENABLE_LEGACY_ROUTES` exists and defaults to false.
4. `alembic heads` returns exactly one head. Record its id. Every migration in this phase chains linearly from it.

Read the handoff pack, `docs/`, `tasks/`, and the Phase 0 report before touching code. Where this prompt contradicts earlier handoff docs, this prompt wins for Phase 1. Specifically it **supersedes**: Batch E item 2 of the hardening prompt (global provider reads) and the roadmap's "announcements migration from `c3f9a6d4e1b2`".

**Verify before changing.** Confirm the current state of each file you touch. If something already exists or conflicts with the plan, do not silently redesign it. Document the conflict, pick the least destructive option, and report it.

**Scope.** This phase delivers Task 6 (announcements, security incidents) plus the foundations the pilot needs: schema additions that cannot be backfilled later, estate and onboarding APIs, and an API contract the frontend can be generated from. It does **not** include the Living Score (Task 7), any frontend, email delivery, password reset, rate limiting, or Docker acceptance work.

Skills: `valora-domain-model`, `valora-api-contracts`, `valora-architecture`, `valora-data-strategy`, `valora-quality-gates`, plus installed security, testing, and code-review workflows. Actually follow them.

## 1. Rules of engagement

Same as the hardening pass:
- The tree is dirty by design. No `reset --hard`, `checkout --`, `clean`, commits, pushes, or PRs.
- Never edit an applied migration. Add new, additive, non-destructive migrations. Before any constraint, check existing data; if violating rows exist, fail with a clear message. Never delete or rewrite user data. Every migration needs a symmetrical `downgrade()` (a downgrade that cannot be safe must refuse with a clear message).
- Routers do HTTP only. Services own rules and authorization. Repositories own queries. Models are never DTOs. Repositories do not commit inside multi-step use cases (flush only, with the service committing once).
- Estate scoping: every estate-scoped resource is loaded through an estate-scoped repository method after `resolve_access`. A client-supplied `estate_id` is never proof of access.
- Honesty rule: never claim live Postgres, migration-apply, or Docker validation unless you ran it. Label everything else "written, not run".
- Loop per batch: failing test first, fix, focused tests, full suite, `compileall`, syntax-focused flake8, `git diff --check`, offline Alembic SQL for the whole chain, short self-review.

### Session protocol (multi-session runs)

This prompt is executed **one batch per session**. The session's task message names the batch (for example "Batch B").

- Do only that batch. Do not start another batch, even if budget remains.
- Read first: the handoff pack, any notes in `docs/progress/` from earlier sessions, and the relevant `.agents/skills/valora-*/SKILL.md` files. Open them directly; they are plain files.
- Implement only the tests in the "tests required" section that belong to your batch.
- Do not commit. The human checkpoints the branch between sessions.
- When finished, or when about 70% of your budget is used, write `docs/progress/<phase>-<batch>.md` covering: done, tests added and passing, written-but-not-run, remaining work, deviations, open questions. Then stop.
- If you stall or loop, stop and say so. Do not keep retrying the same approach.

## 2. Decisions already made (do not ask about these)

| Topic | Decision |
|---|---|
| Path convention | Operational resources stay flat with an `estate_id` query parameter (complaints, work orders, announcements, incidents). Estate-structure resources are nested under `/estates/{estate_id}/...` (invitations, providers). Record this in the ADR. |
| List envelope | `{ "items": [...], "total": int, "page": int, "size": int, "pages": int }`. Query params `page` (default 1, min 1) and `size` (default 20, max 100). Replaces `count` / `page_size` / named list keys. |
| Complaint vs incident | A complaint is something that needs fixing. An incident is something that happened. A broken electric fence is a complaint; a perimeter breach is an incident. |
| Incident visibility | HOA admins see everything. Residents see a summary. Service providers get 403. |
| Estate creation | No public or platform-admin API. Estates, the first HOA admin, and unit import are created by an **operator CLI**. HOA admins then onboard residents and providers through the API. |
| Onboarding | HOA-issued invitation codes. No request-and-approve flow. The legacy `users.hoa_approved` flag is not used for authorization. Note this in docs. |
| Providers | A provider profile belongs to one estate's provisioning flow for now. Cross-estate providers are future work. |

## 7. Batch E — Estates, memberships, onboarding

Run as four sub-batches, **E1 to E4 in order, one session each**. Only E2 adds a migration.

### E2. Invitations (Migration 4)

**Migration 4** creates `estate_invitations` and nothing else, with indexes on `code_hash` (unique), `(estate_id, property_id)`, and `(estate_id)`.

**Table `estate_invitations`:** `invitation_id`; `estate_id` FK `RESTRICT`; `membership_role` (`resident` | `service_provider`); `property_id` (nullable FK); `provider_id` (nullable FK to `service_providers`); `invited_email` (nullable); `code_hash` (unique); `created_by_user_id`; `created_at`; `expires_at` NOT NULL; `redeemed_at`; `redeemed_by_user_id`; `revoked_at`. CHECK: a resident invitation has `property_id` and no `provider_id`; a provider invitation has `provider_id`, no `property_id`, and a non-null `invited_email`.

**Code handling.**
- Generate with `secrets.token_urlsafe(16)` or longer (at least 128 bits). A short human-typeable code would be brute-forceable without rate limiting, so do not add one.
- Store only the SHA-256 hash. The plaintext appears **once**, in the creation response. It is never returned by list or detail endpoints and never logged.
- The code travels in a request **body**, never a path or query string. The `join_url` returned at creation uses a **URL fragment** (`{FRONTEND_BASE_URL}/join#code=...`) so it is not sent to servers or access logs. Add `FRONTEND_BASE_URL` to `Settings` (default `http://localhost:5173`).

**Endpoints:**
- `POST /estates/{estate_id}/invitations` (HOA admin): resident invitations. Body: `property_id` (must be in this estate), optional `invited_email`, `expires_in_days` (default 14, min 1, max 30). Creating a new invitation for a property revokes any earlier pending invitation for it, in the same transaction. Returns the invitation plus `code` and `join_url` once.
- `GET /estates/{estate_id}/invitations` (HOA admin, paginated). `status` is derived: `pending`, `redeemed`, `expired`, or `revoked`.
- `POST /estates/{estate_id}/invitations/{invitation_id}/revoke` (HOA admin).
- `POST /invitations/redeem` (any authenticated user), body `{ "code": "..." }`.

**Redemption rules (resident invitations in this sub-batch).**
- Resolve the code by hash. Claim it with a single conditional `UPDATE ... WHERE redeemed_at IS NULL AND revoked_at IS NULL AND expires_at > now() RETURNING ...`, so two concurrent redemptions yield exactly one success.
- Missing, expired, revoked, and already-used codes all return the **same** 404 with the same message ("This invitation is invalid or has expired."), so the endpoint is not an oracle.
- The caller's global role must be `resident`; if `invited_email` is set it must match the caller's normalised email. Create the `resident` membership with the invited `property_id`. If the user already has that membership, return 409 and **do not** consume the code (roll back the claim).
- The `service_provider` branch is implemented in E3. Until then, provider invitations cannot exist, and the branch returns the same generic 404.
- Document in the ADR that invitation redemption is the **only** API path that grants a non-resident capability. Public registration still creates residents only.

Tests (integration):
- HOA A cannot create, list, or revoke invitations for estate B, and cannot invite a property from B into A.
- Redeeming grants membership **only** for the invited property and estate. Reuse of a code returns 404. Expired and revoked codes return 404. Concurrent redemption (`asyncio.gather`) gives exactly one success.
- Email mismatch is rejected. A non-resident cannot redeem a resident invitation. A user who already has the membership gets 409 and the code stays usable.
- The DB row stores a hash, never the plaintext. The plaintext appears in the creation response only, never in list responses. `join_url` uses a fragment.
- After redeeming, the user can exercise the normal resident flow (report a complaint for the invited unit).
- Registration with `{"role": "hoa_admin"}` still fails and creates no privileged user.

## 9. Explicitly out of scope — do not do now

Living Score and snapshots (Task 7); any frontend; email or notification delivery; password reset and email verification; rate limiting and lockout; duplicate, void, or reassign tools; the CSV complaint-history importer; multi-estate providers; provider verification workflow; a request-and-approve join flow; seed data; Docker acceptance; the `on_event` to lifespan migration.

## 10. Final report format

For each batch: what was found in the real tree, what changed (files), tests added, result. Then:
- a table of every command run with pass or fail (pytest, integration suite if run, compileall, flake8, `git diff --check`, offline Alembic SQL for the full chain, openapi export diff)
- the migration chain in order, with each revision id and one line on what it does
- the new API surface (method, path, role)
- what is **written but not run**
- deviations from this prompt and why; contract changes (envelope, `quoted_cost`, `location_type`, global provider reads)
- newly discovered issues not fixed
- the exact steps for a human to run the integration suite and the CLI bootstrap against a local Postgres

Then **stop**. Do not begin Task 7. Wait for approval.
