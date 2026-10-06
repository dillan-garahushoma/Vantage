# VALORA MVP Capability Map

## Decision record

This map is the implementation boundary for the first production-quality VALORA sandbox increment. It follows the approved product thesis: operational estate data becomes a transparent Living Score. It deliberately excludes the PRD's deferred AI valuation, ROI, public valuation estimate, listing marketplace, and predictive ML work.

The existing backend is retained as the starting point, but the current property, complaint, provider, and analytics scaffolding is not sufficient for estate-scoped operations. The implementation will evolve those modules through additive migrations and replace only the incomplete service contracts needed by the core loop.

## Module graph and delivery order

```text
M1 Identity and estate membership
   |
   +--> M2 Estate, property, and resident context
   |       |
   |       +--> M3 Complaints, immutable lifecycle events, announcements
   |       |       |
   |       |       +--> M4 Providers, work orders, completion, ratings
   |       |               |
   |       |               +--> M5 Security incidents and Living Score snapshots
   |       |
   +--> M6 Typed React client and role-aware application shell
               |
               +--> M7 End-to-end resident -> HOA -> provider -> resident flow
                       |
                       +--> M8 Seed data, tests, browser QA, documentation
```

`M6` may begin once the contracts for `M1` and `M2` are stable. `M7` requires all preceding domain modules. `M8` is continuous, with final acceptance after `M7`.

## Module boundaries

| Module | Responsibility | Does not own |
| --- | --- | --- |
| M1 Identity | JWT authentication, safe public registration, role and estate membership authorization | Operational records |
| M2 Property | Estates and estate-scoped property/unit context | Complaint state transitions |
| M3 Community | Complaint lifecycle, immutable events, estate announcements | Provider execution details |
| M4 Providers | Provider profiles, assigned work orders, completion, resolution ratings | Living Score mathematics |
| M5 Analytics | Deterministic 90-day estate score and immutable versioned snapshots | AI/ML or valuation prediction |
| M6 Frontend | Accessible role-specific interaction and typed API client | Business rules or score calculation |

## MVP acceptance criteria

1. A resident belongs to a specific estate and can submit and view only complaints for a property/unit to which they belong.
2. An HOA administrator can view and manage operational data only for their estate, review a complaint, and assign a verified provider.
3. A provider can view and update only work orders assigned to their linked provider profile.
4. Complaint and work-order transitions preserve historical events and timestamps; they are not overwritten as a single mutable status.
5. A resident can submit exactly one resolution rating for their completed work order.
6. Security incidents, complaint frequency, resolution time, satisfaction, and infrastructure completion contribute to a deterministic, bounded, explainable 90-day estate Living Score.
7. Each calculation persists an immutable `LivingScoreSnapshot` with algorithm version `v1.0.0`.
8. The React application consumes the real `/api/v1` backend through a typed client and supports the completed vertical slice on desktop and mobile.
9. Deterministic seed data creates a coherent South African estate scenario without frontend-only fake metrics.
10. Automated tests, browser verification, security review, and documentation provide evidence for the delivered behaviour.

## Explicit non-goals for this increment

- ML models, LLM/RAG features, predictions, vector databases, and public-dataset dependency.
- Public valuation estimates, ROI projections, listing marketplace workflows, and property sales intelligence.
- Notifications, attachments, native mobile applications, and cross-estate benchmarking.
- Production cloud deployment; Docker remains a local-development concern.
