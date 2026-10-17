# ONB-2 — Estate units (bulk), join codes, resident join and member management

Batch: ONB-2. Status: **implemented and verified end to end, including on live
PostgreSQL.** The integration path that ONB-1 had to leave unrun was executed this
session against a throwaway database: **777 passed, 0 failed.**

Related docs: [ADR-007](../ADR-007-estate-join-codes-and-self-service-membership.md)
(join codes, self-service join, the limiter, the uniqueness decision). Builds on
ADR-006 (role-scoped signup) and ADR-002 (estate authorization).

## What changed

| Area | Added | Notes |
|---|---|---|
| Bulk units | `POST /api/v1/properties/bulk?estate_id=` (`BulkUnitsRequest`, `PropertyService.create_units_bulk`) | All-or-nothing; in-request duplicates and already-used unit numbers rejected before any insert; a losing race rolls the whole batch back with a 409. Complex name and suburb come from the estate row, not the request. Gated by the `hoa_admin` membership rule. |
| Join codes | `GET /api/v1/join-codes/current`, `POST /api/v1/join-codes` | Estate-scoped by `?estate_id=`, `hoa_admin` membership required (re-checked in the service). Generated in the domain layer: 10 chars from a 31-symbol alphabet with no `I/L/O/0/1`, `secrets`, ~49.5 bits. Unique for all time; at most one un-revoked code per estate (partial unique index); rotation is revoke-then-issue in one commit. Returns 404 when an estate has no live code. |
| Resident join | `POST /api/v1/memberships/join` | No approval step. Estate taken from the code row — the body has no `estate_id`. Uniform 404 for unknown/expired/revoked/blank code; 404 for a unit not in that estate; 409 when already a member, including on a lost concurrent race. Membership + `joined` event in one commit. Resident-role gate at the route and in the service. |
| Member management | `GET /api/v1/memberships?estate_id=`, `DELETE /api/v1/memberships/{id}?estate_id=` | Paginated, newest first, optional role filter. Removal deletes the membership row only — account, complaints and history stay — and writes a `removed` event. Admin memberships are not removable. A membership id from another estate is a 404, never a 403. |
| Rate limiting | `JoinAttemptLimiter` (`app/identity/services/`), wired into the membership service and the test suite | 5 failed code attempts per user per 15 minutes → 429. Sliding window, injectable clock, module-level singleton reset between tests. In-process by design (ADR-007). |
| Audit log | `estate_membership_events` model + repository | Append-only: `record` and `list_for_estate` only, no update/delete path. Metadata only — no free-text column, no personal data beyond user ids; user columns `ON DELETE SET NULL` so history survives account deletion. |
| Migration | `b1e4f7a9c2d5_add_estate_join_codes_and_membership_events.py` | Additive, non-destructive, working downgrade: two new empty tables, the nullable `estate_memberships.join_code_id` column, the two partial unique indexes and the event-log index. Offline SQL verified in both directions. |
| Contract | `docs/openapi.json` regenerated | Publishes all five new endpoints; regeneration is byte-identical on re-run (md5 `d25b99204d6981a57f4ef41fd1310e9b` before and after). |

Repositories used by the multi-step paths (`add`, `delete`, `record`, `revoke`)
only flush; each service owns a single commit for its use case, per the
architecture rules. No router contains business logic, and `estate_id` supplied by
a client is never treated as proof of access.

## Tests added and passing

`backend/tests/test_onb2_join_codes_and_membership.py` — **52 tests** (44 policy /
DTO / domain / service tests that run without a database, plus 8
`@pytest.mark.integration` cases). Coverage: the alphabet excluding lookalikes,
the ~49-bit entropy claim, generation length/uniqueness, normalisation, DTO
rejection of extra fields, the limiter's sliding window with an injected clock
(blocking at five, recovery after the window, per-user reset), the absence of any
update/delete path on the event repository, rotation revoking and committing once
(including denial for an estate the admin does not administer), the uniform 404s,
the 409 on an existing membership and on a lost race, the estate-scoped member
list and removal, all-or-nothing bulk creation with rollback, route-level and
body-level gates (no code in a URL or query string), and the offline migration SQL
up and down plus the single-head assertion.

**Integration coverage on a real database:** the full resident journey (admin
signup → bulk units → code → resident join → removal), complaint scoping after a
join, rotation leaving exactly one active code, 429 after five bad codes, a live
cross-estate denial, bulk rollback on a real duplicate, a concurrent duplicate
join creating exactly one membership, and an assertion that a join code never
appears in the logs or an error body.

## Commands run and results (this session)

| Command | Result |
|---|---|
| `docker exec valora_db psql ... -c "SELECT datname FROM pg_database ..."` | Listed 7 databases; confirmation that `valora_onb2_test_20261011` (throwaway) exists and the dev/demo/pilot databases were not used |
| `venv\Scripts\python.exe -m alembic -c alembic.ini heads` | `b1e4f7a9c2d5 (head)` — single head |
| `venv\Scripts\python.exe -m alembic -c alembic.ini current` | `b1e4f7a9c2d5 (head)` on the throwaway database |
| `venv\Scripts\python.exe -m alembic -c alembic.ini downgrade d9f2a4c7e1b3` | `Running downgrade b1e4f7a9c2d5 -> d9f2a4c7e1b3` — no error |
| `venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head` | `Running upgrade d9f2a4c7e1b3 -> b1e4f7a9c2d5` — round-trip clean |
| `venv\Scripts\python.exe -m pytest tests -q` (no `TEST_DATABASE_URL`) | **691 passed, 86 skipped, 0 failed** |
| `venv\Scripts\python.exe -m pytest tests -q` with `TEST_DATABASE_URL` at the throwaway DB | **777 passed, 0 failed** in 587.90s — every previously skipped integration test ran and passed |
| `venv\Scripts\python.exe -m pytest tests/test_onb2_join_codes_and_membership.py -q` (with DB, after the final edit) | **52 passed** in 85.15s |
| `psql` index/constraint inspection on the migrated database | Confirms `uq_estate_join_codes_one_active_per_estate`, `uq_estate_join_codes_code`, `uq_membership_user_estate_join`, `uq_membership_scope`, the event-log index and both new foreign keys are present exactly as the migration writes them |
| `venv\Scripts\python.exe -m compileall -q app` | OK |
| `venv\Scripts\python.exe -m flake8 app tests --count --select=E9,F63,F7,F82 --show-source --statistics` | **0** |
| `git diff --check` | clean (exit 0) |
| `venv\Scripts\python.exe -m app.cli export-openapi` | Regenerated `docs/openapi.json`; re-running produces an identical md5 and the five new paths are published |

ONB-1 reported five pre-existing failures (`test_ai_guard.py` ×4,
`test_ai_pilot_report.py` ×1). Those are gone: both full-suite runs above show
**0 failed**, so the AI-batch regressions were fixed in the meantime and nothing
was skipped or weakened to get there.

## Deviations

1. **The unique index is scoped, not table-wide.** The batch asked for a full
   unique index `uq_membership_user_estate` on `estate_memberships (user_id,
   estate_id)` plus a pre-check that fails on existing duplicates. That invariant
   contradicts the code as it stands, so it was **not** added:
   - ADR-002 and the existing fixtures support one resident holding more than one
     unit membership in one estate — `tests/factories.py` gives `resident_a1` two
     and `tests/test_batch_b_authorization.py` asserts two `property_ids`;
   - `seed_demo.py` deliberately gives one resident two units in one estate, and
     the batch forbids touching that file, so the requested pre-check would have
     made this very migration fail on the demo database;
   - the committed `get_for_user_and_estate` already orders and limits to one row,
     so it does not crash on duplicates — the premise that a duplicate row breaks
     the join path does not hold in the real tree.
   The batch's intent — a resident cannot join the same estate twice, and a
   concurrent duplicate is a 409 rather than a 500 — is delivered by a partial
   unique index on `(user_id, estate_id) WHERE join_code_id IS NOT NULL` plus the
   new nullable `join_code_id` column. `NULL` for every pre-existing row, so the
   upgrade needs no pre-check and cannot fail on populated data.
2. **ADR-007 did not exist.** Five code sites (the join-code domain, the model,
   the limiter, the unit lookup and `conftest.py`) already cited it. It was
   written this session to record those decisions rather than left as a dangling
   reference.
3. **One dead re-export removed.** `membership_service.py` imported and listed
   `ForbiddenException` in `__all__` without using it; nothing imports it from
   there (the tests import it from `app.core.exceptions`). Both lines were dropped.

## Written but not run

- Nothing in this batch's implementation path. The demo seeder, the operator CLIs
  and any migration of the dev, demo or pilot databases were deliberately **not**
  run; all live work used a throwaway `valora_onb2_test_20261011` database, which
  was dropped afterwards.

## Open questions

1. The join-attempt limiter is per-process (ADR-007): two API workers do not share
   the counter and a restart clears every window. Fine for one pilot process,
   insufficient for horizontal scaling.
2. `unit_no` uniqueness is case-sensitive, so `A-1` and `a-1` can coexist; the join
   deterministically takes the lower `unit_id`. Either the constraint should
   become case-insensitive or unit numbers should be normalised on write.
3. Join codes are stored in clear text (deliberately — an admin must read one
   back). At-rest exposure for anyone with database read access is the accepted
   residual.
4. Removing a member does not revoke a code they still hold, so a removed resident
   can re-join while the code is live. Whether removal should force a rotation is
   undecided.
5. No code-expiry or rotation-reminder policy: an estate that never rotates has a
   code that never expires.
