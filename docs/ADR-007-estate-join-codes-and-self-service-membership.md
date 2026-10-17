# ADR-007: Estate Join Codes and Self-Service Membership

## Status

Accepted and implemented. Extends ADR-006: signup gets a person an *account*, a
join code gets them into an *estate*.

## Context

ADR-006 let a person self-register as a resident, an estate admin or a service
provider — but a registered resident still could not reach an estate. Membership
existed only through the operator CLI (`provision_estate.py`) or the demo seeder,
so onboarding residents meant an operator doing it by hand. There was also no way
to stand up the units a resident needs to claim; units had to be created one at a
time.

Two things were needed before onboarding could be self-service, and both are
security decisions rather than features:

1. A credential an estate admin can hand to a resident, that admits that resident
   to *that* estate and nothing else, and that cannot be used to enumerate
   estates.
2. A rule for what "proof of membership" is, now that no human approves each
   resident.

`role` and the estate models were already in place; this ADR is about the secret
and the flow, not the schema shape.

## Decision

### The join code is a shareable secret with a deliberately small surface

* Ten characters drawn from a 31-symbol alphabet that omits the characters people
  confuse when reading a code over the phone or retyping it: `I`, `L`, `O`, `0`
  and `1`. That is `31^10`, about **49.5 bits** of entropy, drawn with
  `secrets` — far beyond what a human could guess, and generated in the domain
  layer (`app/identity/domain/join_code.py`), not in a router.
* **A code is unique for all time.** A later draw can never re-issue a code that
  was revoked or leaked, so an old code cannot be resurrected as valid by
  anything other than an explicit rotation.
* **At most one un-revoked code per estate** (partial unique index on
  `estate_id WHERE revoked_at IS NULL`). Rotation is therefore revoke-then-issue
  in a single transaction, never "add another", so an estate can never be left
  with zero or two live codes.
* **Stored in clear text, on purpose.** The admin has to read it back from
  `GET /api/v1/join-codes/current` to send it to a resident, exactly like a
  password-reset link: a secret in the sense of "not stored hashed", never a
  stored credential. It is consequently **never** placed in a URL path, a query
  string, a log line or an error body; it travels only in an authenticated
  request/response body. The known residual is at-rest exposure — anyone with
  database read access can read a live code.

### Joining is self-service and immediate: no approval step

Possession of the estate's live code **and** a unit number that exists inside
that estate is the whole proof. There is no pending state and no admin approval,
because the admin is the one who chose to hand out the code — asking them to
approve everyone afterwards would be a second decision with no new information.

Rules that follow from that:

* **The estate comes from the code row, never from the request.** `POST
  /memberships/join` takes no `estate_id` at all, so a resident cannot name an
  estate any more than they can claim a unit outside the one the code belongs to.
* **Every unusable code is one uniform 404** — unknown, expired, revoked and
  blank are indistinguishable to the caller. The response never reveals whether a
  code exists.
* **A mistyped unit number is a 404 scoped to that estate**, with the estate's own
  unit list as the only information; a unit number that exists in *another*
  estate does not match.
* **Already a member is a 409**, including when two concurrent joins race: the
  partial unique index makes one of them fail, and the service turns that
  `IntegrityError` into the same 409 rather than a 500.
* The membership row and its `joined` audit event are written in **one commit**.

### Failed guesses are rate limited in-process

Five failed code attempts per user per fifteen minutes raises `RateLimitException`
(429). The window slides rather than resetting, the clock is injectable so the
window is testable without sleeping, and the limiter is a module-level singleton
that the test suite resets between tests.

**This counter lives in the API process's memory.** Two workers do not share it
and a restart forgets every window. That is correct for one pilot estate behind
one process and insufficient the moment the API is scaled horizontally, which is
recorded as an open question below rather than papered over.

### Member management is admin-scoped and non-destructive

* `GET /memberships?estate_id=` and `DELETE /memberships/{id}?estate_id=` both
  require the full credential — the global `hoa_admin` role **and** an
  `hoa_admin` membership of that estate — re-checked in the service, so a
  client-supplied `estate_id` is never proof of access. A membership id from
  another estate is a 404, never a 403 that would confirm the row exists.
* **Removal deletes the membership row only.** The account, complaints and every
  event already written stay where they are, and `/auth/estates` reflects the
  change on its next call. `resident` and `service_provider` memberships are
  removable; an admin's is not, because an estate with no admin would be
  unreachable.

### The membership event log is append-only and metadata-only

`estate_membership_events` records `joined` / `removed` with the estate, the user,
the membership role, the unit and the acting user. There is no free-text column
and no personal data beyond the user ids, so the table is safe to keep for the
life of the estate. The repository exposes only `record` and `list_for_estate` —
no update and no delete — and the user columns are `ON DELETE SET NULL`, so
deleting an account leaves the history intact instead of erasing it.

### Uniqueness is scoped to the self-service path, not the whole table

The batch asked for a full unique index on `estate_memberships (user_id,
estate_id)`. That invariant contradicts the code as it stands and was **not**
added; the intent is delivered by a partial unique index on `(user_id, estate_id)
WHERE join_code_id IS NOT NULL` plus the new `join_code_id` column.

* One person legitimately holds **more than one unit membership in one estate**:
  `tests/factories.py` gives `resident_a1` two, `test_batch_b_authorization.py`
  asserts two `property_ids`, and `seed_demo.py` deliberately gives one resident
  two units.
* A full unique index would therefore fail on a populated/demo database, and the
  pre-check the batch asked for would make this migration itself fail there.
* Scoping to `join_code_id` — `NULL` for every pre-existing row — keeps the
  upgrade safe on live data: a nullable column with a NULL predicate cannot
  create a duplicate, so no pre-check is needed. Operator-provisioned and seeded
  multi-unit memberships are unaffected, and self-service cannot join the same
  estate twice.

### Bulk unit creation makes onboarding practical

`POST /properties/bulk?estate_id=` creates an estate's units in one call, gated by
the same `hoa_admin` membership rule. It is **all or nothing**: duplicates inside
the request or unit numbers that already exist in the estate are rejected before
anything is inserted, and a losing database race rolls the whole batch back with
a 409. The estate's `complex_name` and `suburb` are taken from the estate row, not
from the request.

### Unit numbers are matched case- and padding-insensitively, but uniqueness is not

`unit_no` uniqueness in the schema is case-sensitive, so two units could in
principle differ only by case. The join lookup therefore normalises case and
whitespace and picks the **lowest `unit_id`** when more than one row matches, so
the result is deterministic instead of raising.

## Consequences

An estate can be filled with residents without an operator in the loop, and the
blast radius of a leaked code is one estate's units — a leaked code admits a
person to units that admin already created, in an estate whose code they chose to
share, and it can be revoked by rotating.

The costs are explicit: a code is readable at rest, the limiter is per-process,
and correctness of "one unit, one resident" rests on the estate's own unit
numbers being meaningful rather than on any ownership claim.

## Open questions

1. **The limiter is in-process.** Scaling the API to more than one worker needs a
   shared counter (Redis or a table), and a restart currently clears the window.
   Not needed for a single pilot process; required before horizontal scaling.
2. **`unit_no` uniqueness is case-sensitive**, so `A-1` and `a-1` can both exist
   in one estate and the join deterministically takes the lower id. Either the
   constraint should become case-insensitive or unit numbers should be
   normalised on write.
3. **No code rotation reminder or expiry policy.** An estate that never rotates
   has a code that never expires; whether codes should expire by default (and who
   is told) is a product decision.
4. **Removing a member does not revoke a code they still hold.** A removed
   resident with the estate's live code can re-join; whether removal should be
   accompanied by rotation is unresolved.

## Verification

`backend/tests/test_onb2_join_codes_and_membership.py` (52 tests) pins the
alphabet and entropy, normalisation, DTO rejection, the limiter's sliding window
with an injected clock, the append-only repository shape, rotation in one commit,
the uniform 404s, the 409 on a duplicate or a lost race, the estate-scoped member
list and removal (including refusal of an admin membership and a 404 across
estates), all-or-nothing bulk creation, the route/DTO gates, and the offline
migration SQL in both directions. Integration cases run against a real database
when `TEST_DATABASE_URL` is set and skip otherwise; the migration's upgrade and
downgrade were both exercised on a throwaway PostgreSQL database.
