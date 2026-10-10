> **SESSION TASK: execute ONLY Batch F.** Do not start any other batch. Follow the session protocol below.

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

## 8. Batch F — Documentation and report

- ADR-003 (estates, onboarding, invitations, operator CLI, role-grant rules) and ADR-004 (complaint taxonomy, SLA policy v1.0.0, incident visibility, path convention). Update ADR-001/002, the roadmap migration chain, `VALORA_IMPLEMENTATION_STATUS.md`, and `tasks/todo.md` (add Phase 1 sub-tasks; tick Task 6 only after its tests pass).
- Commit `docs/openapi.json`. Document the API surface and local setup, including the CLI bootstrap steps for a fresh database (create estate, create HOA admin, import units, invite a resident).
- Record limitations honestly: no rate limiting on redemption (top candidate for Phase 5), invitations are shared manually because email delivery is not built, anonymous complaints remain inferable from `unit_id`, SLA targets are unvalidated defaults, legacy list endpoints still use the old envelope.

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
