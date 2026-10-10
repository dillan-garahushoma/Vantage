> **SESSION TASK: execute ONLY Batch C.** Do not start any other batch. Follow the session protocol below.

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

## 5. Batch C — Foundation schema (Migration 2)

One additive migration with these changes. All new columns are nullable or have safe defaults so legacy rows stay valid.

**Estates.** Add `data_origin` (`demo` | `pilot` | `production`, NOT NULL, `server_default 'demo'` so legacy rows are safe, with a CHECK constraint), `unit_count` (nullable integer, CHECK > 0), and `onboarded_at` (nullable timestamptz).

**Complaints.**
- `location_type` (`unit` | `common_area` | `perimeter`, NOT NULL, `server_default 'unit'`) and `location_detail` (nullable string, max 120, for example "Main gate").
- Make `unit_id` **nullable** and add a CHECK that `unit_id` is not null if and only if `location_type = 'unit'`. Legacy rows satisfy this because they are all `unit` with a unit id. The downgrade must refuse if any row has a null `unit_id`.
- `review_due_at` and `resolution_due_at` (nullable timestamptz) and `sla_policy_version` (nullable string). Do **not** backfill them for legacy rows.
- Do not add a subcategory column.

**Work orders.** Add `quoted_cost` (nullable `Numeric(12,2)`, CHECK >= 0). Semantics: `quoted_cost` is the HOA's quote at assignment; the existing `job_cost` becomes the actual final cost set by the provider. Rename `WorkOrderCreate.job_cost` to `quoted_cost`. This is a deliberate contract change, because no frontend exists yet.

**Category taxonomy (code, not a table).** Add a `ComplaintCategory` enum used by `ComplaintCreate` validation:
`water_and_plumbing`, `electrical_and_power`, `gates_and_access`, `security_and_perimeter`, `roads_and_paving`, `grounds_and_landscaping`, `waste_and_refuse`, `noise_and_nuisance`, `common_facilities`, `other`.
Responses keep `category` as a plain string, because legacy rows contain free text. Do not add a DB CHECK on category.

**SLA policy (code).** Create one module (for example `app/community/domain/sla_policy.py`) with `SLA_POLICY_VERSION = "1.0.0"` and calendar-hour targets. These are MVP assumptions, not validated facts. State that in the module docstring and the ADR.

| Priority | Review within | Resolve within |
|---|---|---|
| urgent | 4 h | 24 h |
| high | 24 h | 72 h |
| normal | 48 h | 168 h |
| low | 72 h | 336 h |

On complaint creation, compute `review_due_at` and `resolution_due_at` from the same `now` used for `created_at` (set `created_at` explicitly), and store them with `sla_policy_version`. Changing the policy later never rewrites stored due dates.

**Service and DTO changes.**
- `ComplaintCreate`: `category` becomes the enum; add `location_type` (default `unit`) and `location_detail`; `unit_id` becomes optional and required if and only if `location_type == 'unit'` (model validator).
- For `unit` complaints, residents may report only for a unit in `access.property_ids` (admins: any unit in the estate). For `common_area` and `perimeter`, any resident or admin member of the estate may report.
- `ComplaintResponse` gains `location_type`, `location_detail`, `review_due_at`, `resolution_due_at`, and `is_overdue: bool | None`, computed in the service (not stored). It is `None` when the complaint has no due dates (legacy). It is true when the complaint is not resolved or rated and either the review is due while the status is `submitted`, or the resolution due date has passed.
- `unit_id` in responses becomes `int | None`.

Tests: XOR rule (422 for violations), enum rejection, due dates and policy version persisted, `is_overdue` for each status and for legacy nulls, common-area complaint by a resident, resident cannot report a unit that is not theirs, legacy-style row (null due dates, `location_type unit`) still serialises.

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
