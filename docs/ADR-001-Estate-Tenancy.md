# ADR-001: Estate Tenancy Boundary

## Status

Accepted and implemented for the Core Operational Intelligence MVP. Authorization details are recorded in [ADR-002](ADR-002-estate-authorization.md).

## Context

The original schema had `properties` that behaved as units, but no estate entity or reliable property-to-estate relationship. Existing `complex_name` and a user's free-text `unit_no` cannot safely establish tenancy or authorization.

## Decision

`Estate` is VALORA's tenant boundary. `EstateMembership` explicitly records a user's estate membership and optional property/unit scope. `properties.estate_id` is a nullable foreign key; unmapped legacy properties remain unassigned and are excluded from estate-scoped workflows. New operational records carry an estate relationship.

## Consequences

This avoids inventing ownership from legacy text fields and enables server-side authorization. Estate access is derived from persisted membership rather than a global user role; membership uniqueness and the dual-role check are specified in ADR-002. The current migration head is `d4a7e1c9b3f2`; live database application and legacy-row mapping remain operational follow-ups.
