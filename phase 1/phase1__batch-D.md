> **SESSION TASK: execute ONLY Batch D.** Do not start any other batch. Follow the session protocol below.

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

## 6. Batch D — Security incidents (Task 6b, Migration 3)

Keep this deliberately lean. It exists to feed one Living Score component.

**Table `security_incidents`:**
- `incident_id` PK; `estate_id` NOT NULL FK `RESTRICT`
- `property_id` nullable FK to `properties.unit_id` `RESTRICT` (the service must verify it belongs to the same estate)
- `category`: `perimeter_breach`, `access_control_failure`, `theft_or_burglary`, `vandalism`, `suspicious_activity`, `patrol_or_guarding_issue`, `other`
- `severity`: `low`, `medium`, `high`, `critical`
- `occurred_at` timestamptz NOT NULL
- `status`: `open`, `resolved`
- `description` (text, nullable, max 5000), `resolution_notes` (nullable), `resolved_at` (nullable)
- `created_by_user_id` and `resolved_by_user_id` (nullable FK to `users`, `ON DELETE SET NULL`)
- `created_at`, `updated_at`
- CHECK constraints: severity and status sets; `(status = 'resolved') = (resolved_at IS NOT NULL)`; `resolved_at >= occurred_at`
- Index `ix_security_incidents_estate_occurred (estate_id, occurred_at)` for the Living Score window query. No other indexes unless justified.

**Rules.**
- `occurred_at` is timezone-aware (`ensure_utc`) and must not be in the future (allow 5 minutes of clock skew). Backdating is allowed so history can be entered later.
- Resolve requires `resolution_notes` (min 5 characters). The server sets `resolved_at`, never the client. Resolving twice returns 409.
- A resolved incident is immutable. PATCH on a resolved incident returns 409. While open, an HOA admin may correct category, severity, `occurred_at`, description, and `property_id`.
- Incidents do not get an events table. Do not build a security-management platform.

**Endpoints** (flat, with `estate_id` query parameter, `Page` envelope):
- `POST /incidents` (HOA admin)
- `GET /incidents` with filters `status`, `severity`, `category`, `from`, `to`, and `sort` (allow-listed)
- `GET /incidents/{id}`
- `PATCH /incidents/{id}` (HOA admin, open only)
- `POST /incidents/{id}/resolve` (HOA admin)

**Visibility** uses one DTO. The fields `property_id`, `description`, `resolution_notes`, `created_by_user_id`, and `resolved_by_user_id` are populated **only for estate admins** and are `null` for residents. Residents always see `id`, `estate_id`, `category`, `severity`, `occurred_at`, `status`, `resolved_at`. Service providers get 403 on every incident endpoint.

Tests (integration): full lifecycle; resident sees nulls for the HOA-only fields (assert at the JSON level); provider forbidden; an incident id from estate B with `estate_id=A` returns 404 and with `estate_id=B` returns 403; `property_id` from another estate returns 404 or 422 (choose, and justify); future `occurred_at` returns 422; filters and pagination; resolved incident PATCH returns 409; resolve twice returns 409; DB CHECK rejects an inconsistent resolved row (raw insert).

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
