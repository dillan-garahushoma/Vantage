# ADR 001 Estate Tenancy Boundary

## Status

Accepted for the Core Operational Intelligence MVP.

## Context

The existing schema has `properties` that behave as units, but no estate entity or reliable property-to-estate relationship. Existing `complex_name` and a user's free-text `unit_no` cannot safely establish tenancy or authorization.

## Decision

`Estate` is introduced as VALORA's tenant boundary. `EstateMembership` explicitly records a user's estate membership and optional property/unit scope. `properties.estate_id` is added as a nullable foreign key. All new operational records and seed data will require an estate relationship; existing legacy rows remain unassigned until an administrator performs a controlled mapping.

## Consequences

This avoids inventing ownership from legacy text fields and enables server-side authorization in the next task. A legacy property without `estate_id` is deliberately excluded from estate-scoped operational workflows until it is assigned.
