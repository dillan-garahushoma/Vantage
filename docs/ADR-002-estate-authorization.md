# ADR-002: Estate Authorization

## Status

Accepted and implemented.

## Context

A user's global role alone cannot prove access to a particular estate. Residents can have multiple unit memberships, and a user can participate in different estates under different membership roles.

## Decision

Estate-scoped services resolve persisted membership through `EstateAuthorizationService.resolve_access` into an immutable `EstateAccess`. It contains the user's estate membership roles and property IDs, along with derived estate-admin and estate-provider capabilities.

Administrative or provider capability requires both matching credentials: the global `User.role` and a matching role in at least one membership for the requested estate. `require_role` enforces both. Resident property operations must use the resolved property IDs, not one assumed membership row.

Membership rows are unique by `(user_id, estate_id, property_id)`. A PostgreSQL partial unique index additionally permits at most one estate-level row per `(user_id, estate_id)` where `property_id IS NULL`. Memberships for distinct properties and distinct estates remain valid.

## Consequences

Membership is the tenant authorization boundary; a global role grants no cross-estate access. Estate-scoped lookups filter by both estate and resource ID so foreign-estate resources are not exposed.

Unassigned legacy properties are not inferred into a tenant from free-text fields. Anonymous complaints suppress the author's actor ID in complaint events for other viewers, but the HOA may still infer the author from the complaint's `unit_id`; this is a known limitation, not a guarantee of anonymity from the HOA.

## Verification and follow-ups

The service, authorization tests, and membership uniqueness metadata are covered by Phase 0 batches B and D. Offline migration SQL generation was verified; application against a live PostgreSQL database remains unverified.
