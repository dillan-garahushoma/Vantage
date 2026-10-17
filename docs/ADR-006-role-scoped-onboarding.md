# ADR-006: Role-Scoped Onboarding and Platform-Operator Role

## Status

Accepted and implemented. Supersedes the registration clause of ADR-002 and the
earlier Phase 0 decision that "public registration creates residents only" and
that provider records are written by any global `hoa_admin`.

## Context

The original onboarding contract let a person self-register only as a `resident`.
We now need self-service signup for the two roles a real estate actually needs at
the door: the HOA administrator who is creating a new estate, and the service
provider who wants to be listed. Two problems followed from the old model:

1. **A self-registered `hoa_admin` could act platform-wide.** Several endpoints
   were gated by the global `hoa_admin` role alone. The sharpest was the provider
   register: any `hoa_admin` could create a provider, edit it, and set
   `verified` — a VALORA-level trust decision, not an estate one. Listing and sale
   writes were likewise gated by the global role with no check that the acting
   admin administered the estate the unit belonged to, so a global `hoa_admin`
   could create a listing or record a sale for a foreign estate (including a
   legacy unit with `estate_id IS NULL`).
2. **There was no operator role.** Nothing distinguished VALORA's own staff from
   an estate's administrator. Provider trust (`verified`) had no owner.

`role` is a `String(20)` column, so adding a role value needs no schema
migration.

## Decision

**Public signup is role-scoped by `account_type`.** The only self-selectable
account types are `resident` (the default), `estate_admin` and
`service_provider`. A `role` field is still rejected; the stored role always
follows from `account_type`.

* `resident` — unchanged: one user row, role `resident`.
* `estate_admin` — creates the user (role `hoa_admin`), a new non-demo estate, and
  an estate-level membership (`hoa_admin`, no property) in **one transaction**,
  committed once. A duplicate estate name is `409` and leaves no orphan user.
* `service_provider` — creates the user (role `service_provider`) and a linked
  provider profile (`verified=false`, `emergency_available=false`) in **one
  transaction**. No estate membership is granted; estate access is provisioned
  separately.

`platform_admin`, `estate_agent` and `investor` are **not** self-selectable.

**`platform_admin` is an operator-only role.** It is the only role that may create
or update service-provider records (including `verified`). It is granted solely
through `scripts/assign_platform_admin.py`, which is dry-run by default, prints
the redacted target database, refuses a demo-looking database without an explicit
flag, supports `--expect-database`, and never reads `.env`. The role grants no
estate access: every estate-scoped action still requires a persisted membership.

**Estate-admin writes are estate-scoped.** Listing and sale creation/editing
require the global `hoa_admin` role **and** an `hoa_admin` membership in the
estate that owns the unit. A legacy `NULL`-estate unit is denied outright. This
extends ADR-002's dual-credential rule to these two writes.

## Consequences

Self-registering an estate no longer confers any cross-estate or platform power.
The blast radius of a hostile signup is limited to the estate it created. Provider
trust decisions belong to VALORA's operators, not to estates.

A `platform_admin` is a platform-wide credential and must be handled like one; the
operator CLI is the only supported path to grant it, and its dry-run and
demo-database guards are the safety rail. There is currently no UI or API to grant
or revoke it, by design.

## Verification

`backend/tests/test_onb1_role_scoped_signup.py` pins: rejection of `role`,
unknown and non-selectable `account_type`s, the required estate/provider payloads,
the platform-admin guard on provider writes, the estate-membership rule for
listing and sale writes, one-transaction signup with rollback, the cross-estate
sweep, provider signup granting zero estate access, `platform_admin` being
unobtainable through any public endpoint, no password in the logs, and the
operator CLI's dry-run, apply, missing-account, demo-database, `.env` and redaction
behaviour. Integration cases skip without `TEST_DATABASE_URL`.
