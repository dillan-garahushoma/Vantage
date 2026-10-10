# ADR-003: Legacy Isolation and Provider Rating Writes

## Status

Accepted and implemented.

## Decision

Legacy listings, sales, review routes, and provider write routes are isolated behind `ENABLE_LEGACY_ROUTES`, which defaults to `false`. With the default setting, the legacy routes are omitted from OpenAPI and return 404. Legacy property-score types are explicitly named `LegacyPropertyScore*`, and the legacy score endpoint is deprecated. Provider reads are restricted to an HOA administrator with estate membership or a provider accessing their own profile.

`MaintenanceWorkOrder.resident_rating` is the canonical rating write. `WorkOrderService.rate_work_order` locks the estate-scoped work-order row, verifies that the requesting resident raised the complaint and that the work is complete and unrated, then persists the rating and updates the provider's cached average and count from all rated work orders. These writes are handled as one transaction. No legacy provider-review route or alternate writer may update the canonical work-order rating aggregate.

## Consequences

Disabling legacy routes reduces accidental use of transitional APIs without deleting legacy data. The flag is an explicit compatibility switch, not authorization by itself; exposed operations still enforce their access rules.

Provider `avg_rating` and `total_reviews` are derived caches. When correcting or rebuilding them, recompute from canonical rated work orders rather than treating the cached provider columns or legacy review records as the source of truth.

## Verification and follow-ups

Batch E tests cover disabled/enabled route behavior and provider read restrictions. Batch C tests cover rating aggregation. Database-backed concurrency and atomicity checks still require the integration test database.
