# VALORA Backend Architecture Consolidation & Implementation Prompt

## Agent Objective

You are working inside the **current `valora-live` repository**.

Your task is to **consolidate and repair the backend architecture**, not rewrite the project and not discard working implementation.

The current backend is a transitional state created by merging:

1. The original VALORA backend architecture.
2. Backend implementation added by the team while the original author was absent.
3. A later Codex attempt to transplant the original architecture into `valora-live`.

The current state contains duplicated architectural patterns:

- domain modules (`identity`, `property`, `community`, `providers`, `analytics`)
- top-level `models/`
- top-level `routers/`
- top-level `services/`
- duplicated configuration/database locations (`core`, `config`, `database`, `db`, `shared`)

The goal is to preserve useful implementation while establishing **one canonical backend architecture**.

Do not perform a blind rewrite.

---

# 1. Source of Truth

Use the following architectural sources as the basis for this task:

- Original VALORA backend structure: domain-oriented modules with `api / domain / repositories / schemas / services`.
- Current `valora-live` implementation: preserve useful SQLAlchemy models, API behavior, authentication, valuation/ROI, complaints, providers, announcements, and existing tests.
- Analysis/design data model: preserve the conceptual entities and relationships.
- Development roadmap: business capabilities should be implemented as coherent domain slices.

The system's intended scope includes:

- User management and authentication
- Property intelligence
- AI/rule-based valuation
- Rental yield and ROI
- Complaint and maintenance management
- Service provider directory and verification
- HOA announcements
- Analytics / Living Score
- Role-based access control

The MVP is for a **single housing complex/community**.

Do not introduce unrelated product scope such as banking, mortgages, property purchasing transactions, or legal conveyancing.

---

# 2. Architectural Decision

Adopt a **modular monolith with domain-oriented Clean Architecture**.

The backend must have:

- one application entry point
- one central API router
- domain-owned API routers
- domain-owned application services
- domain-owned repositories
- domain-owned schemas
- domain-owned domain entities
- domain-owned persistence models where appropriate
- shared infrastructure only for genuinely cross-cutting concerns

Do NOT use multiple competing organizational patterns.

The canonical rule is:

> Business capability owns its API, domain, repository, schema, service, and persistence concerns.

---

# 3. Canonical Backend Structure

The final backend should converge toward this structure:

```text
backend/
├── Dockerfile
├── alembic.ini
├── requirements.txt
├── docker-compose.yml
├── alembic/
│   ├── README
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── router.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   ├── logging.py
│   │   └── security.py
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── database.py
│   │   └── session.py
│   │
│   ├── common/
│   │   ├── __init__.py
│   │   ├── enums.py
│   │   ├── pagination.py
│   │   └── validators.py
│   │
│   ├── identity/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── dependencies.py
│   │   │   └── router.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   └── entities.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── role.py
│   │   │   ├── session.py
│   │   │   └── login_attempt.py
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   └── user_repository.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   └── user.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── auth_service.py
│   │       ├── jwt_service.py
│   │       └── password_service.py
│   │
│   ├── property/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── router.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   └── entities.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── property.py
│   │   │   ├── listing.py
│   │   │   └── sale.py
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   └── property_repository.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── property.py
│   │   │   ├── listing.py
│   │   │   └── valuation.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── property_service.py
│   │       ├── valuation_service.py
│   │       └── roi_service.py
│   │
│   ├── community/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── router.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   └── entities.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── complaint.py
│   │   │   ├── maintenance_work_order.py
│   │   │   └── announcement.py
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── complaint_repository.py
│   │   │   └── announcement_repository.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── complaint.py
│   │   │   ├── work_order.py
│   │   │   └── announcement.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── complaint_service.py
│   │       ├── maintenance_service.py
│   │       └── announcement_service.py
│   │
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── router.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   └── entities.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── service_provider.py
│   │   │   └── review.py
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   └── provider_repository.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── provider.py
│   │   │   └── review.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── provider_service.py
│   │       └── review_service.py
│   │
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── router.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   └── entities.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── ai_analytic.py
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   └── analytics_repository.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── analytics.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── living_score_service.py
│   │       └── analytics_service.py
│   │
│   └── ml/
│       ├── __init__.py
│       ├── inference/
│       ├── models/
│       ├── preprocessing/
│       └── training/
│
└── tests/
    ├── __init__.py
    ├── identity/
    ├── property/
    ├── community/
    ├── providers/
    └── analytics/
```

The exact number of files may differ. The **architectural ownership and boundaries must not**.

---

# 4. Mandatory Migration Rules

## 4.1 Preserve Working Functionality

Before moving code:

- inspect existing imports
- inspect route registration
- inspect model relationships
- inspect Alembic configuration
- inspect existing tests
- inspect frontend API expectations

Do not delete functionality merely because it is located in the wrong directory.

Move and adapt it.

---

## 4.2 Eliminate Top-Level `models/`

The current:

```text
app/models/
```

contains persistence models for multiple domains.

These models must be moved into their owning domain.

Examples:

```text
models/user.py
→ identity/models/user.py

models/session.py
→ identity/models/session.py

models/login_attempt.py
→ identity/models/login_attempt.py

models/property.py
→ property/models/property.py

models/listing.py
→ property/models/listing.py

models/sale.py
→ property/models/sale.py

models/complaint.py
→ community/models/complaint.py

models/maintenance_work_order.py
→ community/models/maintenance_work_order.py

models/announcement.py
→ community/models/announcement.py

models/service_provider.py
→ providers/models/service_provider.py

models/review.py
→ providers/models/review.py

models/ai_analytic.py
→ analytics/models/ai_analytic.py
```

Preserve SQLAlchemy relationships and Alembic compatibility.

---

# 5. Eliminate Top-Level `routers/`

The current:

```text
app/routers/
```

must not remain as a second routing architecture.

Move each feature router into its owning domain:

```text
routers/auth/
→ identity/api/

routers/users/
→ identity/api/

routers/property/
→ property/api/

routers/valuation/
→ property/api/

routers/roi/
→ property/api/

routers/complaints/
→ community/api/

routers/announcements/
→ community/api/

routers/providers/
→ providers/api/
```

The only global router should be:

```text
app/api/router.py
```

Its responsibility is composition only.

It should include the domain routers.

It must not contain business logic.

---

# 6. Eliminate Top-Level `services/`

Move service implementations into their owning domains.

Examples:

```text
services/property_service/
→ property/services/property_service.py

services/valuation_service/
→ property/services/valuation_service.py

services/roi_service/
→ property/services/roi_service.py

services/complaint_service/
→ community/services/complaint_service.py
```

If a service is genuinely cross-domain, do not arbitrarily place it into a domain. First determine whether it belongs in:

- analytics
- a domain application service
- or a narrowly scoped shared infrastructure component

Do not create another generic `services/` dumping ground.

---

# 7. Configuration and Database Consolidation

The current repository contains competing locations such as:

```text
app/config
app/database
app/core/
app/db/
app/shared/
```

The canonical locations are:

```text
app/core/config.py
app/core/security.py
app/core/exceptions.py
app/core/logging.py

app/db/base.py
app/db/database.py
app/db/session.py
```

Move functionality into these locations.

Remove obsolete duplicate modules after imports are migrated.

Do not maintain aliases indefinitely just to preserve bad structure.

---

# 8. `shared/` Policy

Do NOT use:

```text
app/shared/
```

as a general dumping ground.

Only create shared modules when they are genuinely cross-cutting and domain-neutral.

Existing configuration/database/logging responsibilities should move to:

```text
core/
db/
common/
```

Use `common/` only for genuinely reusable application-level utilities such as:

- enums
- pagination
- validators

---

# 9. Domain Ownership Rules

Use these ownership boundaries:

### Identity

Owns:

- users
- roles
- authentication
- authorization
- JWT
- password hashing
- sessions
- login attempts

### Property

Owns:

- properties
- listings
- sales/historical property data
- property search
- valuation
- rental yield
- ROI
- property intelligence inputs

### Community

Owns:

- complaints
- maintenance work orders
- complaint lifecycle
- announcements
- resident community operations

### Providers

Owns:

- service providers
- provider applications
- HOA verification
- provider ratings/reviews

### Analytics

Owns:

- Living Score
- Property Health / community intelligence calculations
- analytics aggregation
- future ML integration

### ML

Owns:

- preprocessing
- training
- model artifacts/interfaces
- inference

ML must not become the owner of ordinary business logic.

---

# 10. Critical Product Relationship

Do not architect Property Intelligence and Community Management as unrelated systems.

VALORA's core differentiation is the relationship between:

```text
Community quality
      ↓
Complaints
Maintenance
Provider performance
Resident satisfaction
      ↓
Living Score / Property Health
      ↓
Property Intelligence
      ↓
Valuation / ROI / Investment Insight
```

The roadmap explicitly identifies Living Score as a differentiator and places it between community data and property intelligence.

The initial Living Score should be deterministic/rule-based. ML should be introduced only after sufficient historical data exists.

Do not invent an ML dependency for functionality that can operate deterministically today.

---

# 11. Domain vs ORM Model Separation

Do not treat SQLAlchemy models as domain entities.

Use:

```text
domain/entities.py
```

for business concepts/rules where needed.

Use:

```text
models/*.py
```

for SQLAlchemy persistence models.

Repositories mediate persistence access.

Services orchestrate business use cases.

API routers translate HTTP requests into application operations.

Desired dependency direction:

```text
API
 ↓
Application Service
 ↓
Repository Interface
 ↓
Persistence Implementation
 ↓
SQLAlchemy Model
 ↓
PostgreSQL
```

Business logic must not be embedded inside route handlers.

Avoid direct database manipulation from routers.

---

# 12. Central Router

`app/api/router.py` should be the only application-level route composition point.

Conceptually:

```text
main.py
   ↓
app.api.router
   ├── identity.api.router
   ├── property.api.router
   ├── community.api.router
   ├── providers.api.router
   └── analytics.api.router
```

Keep route prefixes, tags, response models, authentication dependencies and existing frontend contracts stable unless there is a compelling reason to change them.

---

# 13. Authentication and RBAC

Preserve the existing authentication implementation where functional.

The system requires role-based access for:

- Casual Visitor
- Resident
- Investor
- Estate Agent
- HOA Admin

Service Provider also exists as a system actor in the analysis model and should be handled consistently with the implemented authorization model.

Do not scatter authorization logic across routers.

Create reusable dependencies/policies under:

```text
identity/api/dependencies.py
```

or an appropriately owned identity authorization module.

Every protected endpoint must have an explicit authorization boundary.

Do not rely on frontend route protection as security.

---

# 14. Database / Alembic

After moving models:

1. Ensure all ORM models are imported into the SQLAlchemy metadata/base registry.
2. Verify relationships and foreign keys.
3. Verify Alembic can discover metadata.
4. Run migrations against a clean database.
5. Run migrations against the current development database where possible.
6. Do not silently drop data.
7. Do not regenerate destructive migrations merely to make the tree look clean.

If a migration is required because the architecture changes database ownership without changing schema semantics, prefer a safe migration strategy.

---

# 15. Environment and Secrets

The current structure contains environment files under backend/application locations.

Do not commit real secrets.

Ensure:

```text
.env
```

is ignored.

Maintain:

```text
.env.example
```

with required variable names but no secrets.

Configuration must be loaded from one canonical settings implementation.

---

# 16. Docker

There are currently both:

```text
root docker-compose.yml
backend/docker-compose.yml
```

Do not automatically delete either.

First determine what each is actually responsible for.

The desired outcome is:

- one authoritative development composition strategy
- no duplicated service definitions
- no conflicting database configuration
- backend starts consistently
- API can reach PostgreSQL
- environment variables are explicit

If root `docker-compose.yml` is the intended full-stack composition, keep it and make `backend/docker-compose.yml` either clearly scoped or remove it if redundant.

Do not leave two competing definitions unexplained.

---

# 17. API Compatibility

Before changing endpoint paths or payload contracts:

- inspect frontend API calls
- inspect backend routers
- inspect tests
- identify current endpoint behavior

Prefer internal architectural migration over unnecessary API breaking changes.

If an endpoint is already consumed by the frontend, preserve it unless it is demonstrably incorrect.

---

# 18. Testing Requirements

Do not consider the migration complete merely because imports work.

At minimum verify:

### Application startup

```text
FastAPI application imports successfully.
```

### Database

```text
SQLAlchemy metadata loads.
Alembic can inspect metadata.
Database connection succeeds.
```

### Authentication

```text
Registration works.
Login works.
JWT generation works.
Protected endpoint rejects unauthenticated access.
RBAC rejects unauthorized roles.
```

### Domain routing

Verify representative endpoints for:

- property
- valuation
- ROI
- complaints
- providers
- announcements
- analytics

### Existing frontend

Run the frontend tests that exercise API contracts.

Do not break the frontend while reorganizing the backend.

---

# 19. Quality Gates

Before declaring completion, run:

```text
python -m compileall backend/app
```

Run the project's backend test suite.

Run Alembic checks.

Start the FastAPI application.

Verify route registration.

Run the frontend test suite.

Run the frontend build.

Fix import errors, circular dependencies, missing exports and broken route registrations.

---

# 20. Architecture Anti-Patterns Forbidden After Migration

The final backend must NOT contain:

```text
app/models/
app/routers/
app/services/
app/shared/
app/config
app/database
```

as duplicate architectural locations.

Do not create:

```text
utils/
helpers/
misc/
common_services/
generic_services/
```

as dumping grounds.

Do not place business logic in:

```text
main.py
api/router.py
```

Do not make routers directly query SQLAlchemy models unless the existing project deliberately uses that pattern and it is being migrated as part of the consolidation.

Do not duplicate the same entity across multiple ORM model locations.

Do not create duplicate authentication implementations.

Do not create duplicate database session implementations.

---

# 21. Migration Strategy

Perform the work in this order.

## Step 1 — Inventory

Inspect:

- all backend Python files
- imports
- routers
- services
- models
- schemas
- repositories
- database configuration
- Alembic
- tests
- frontend API calls

Do not modify code yet.

## Step 2 — Map Ownership

Create an internal migration map:

```text
Current file → Canonical location
```

Ensure every existing implementation has exactly one owner.

## Step 3 — Move Persistence Models

Move SQLAlchemy models into their domains.

Fix imports.

Verify metadata.

## Step 4 — Move Services

Move feature services into domain `services/`.

Fix imports.

## Step 5 — Move Routers

Move feature routers into domain `api/`.

Fix imports.

## Step 6 — Consolidate Core Infrastructure

Move configuration/security/logging/database concerns into:

```text
core/
db/
common/
```

## Step 7 — Consolidate Central Routing

Make:

```text
app/api/router.py
```

the single composition point.

## Step 8 — Remove Obsolete Structure

Only after all imports and tests pass, remove obsolete duplicate directories/files.

## Step 9 — Verify Database

Run Alembic and database verification.

## Step 10 — Verify Application

Run backend and frontend tests and startup/build checks.

---

# 22. Do Not Rewrite Working Business Logic

This is a refactoring task first.

Do not use this task as an excuse to:

- redesign valuation algorithms
- redesign the frontend
- introduce microservices
- introduce Redis
- introduce Kafka
- introduce CQRS
- introduce event sourcing
- add unnecessary abstractions
- replace FastAPI
- replace SQLAlchemy
- replace PostgreSQL

The MVP is a modular monolith.

Architect for clean boundaries, not hypothetical scale.

---

# 23. Expected Final Result

The final backend should communicate its architecture immediately to a new developer.

A developer should be able to answer:

> Where does property logic live?

`app/property/`

> Where does complaint logic live?

`app/community/`

> Where does provider logic live?

`app/providers/`

> Where does authentication live?

`app/identity/`

> Where does Living Score live?

`app/analytics/`

> Where are global HTTP routes composed?

`app/api/router.py`

> Where is database infrastructure?

`app/db/`

> Where is application configuration/security/logging?

`app/core/`

There must be one obvious answer to each question.

---

# 24. Final Acceptance Criteria

The task is complete only when all of the following are true:

- [ ] Existing useful backend functionality has been preserved.
- [ ] Backend follows the canonical domain-oriented structure.
- [ ] No duplicate top-level `models/`, `routers/`, or `services/` architecture remains.
- [ ] Configuration has one canonical implementation.
- [ ] Database infrastructure has one canonical implementation.
- [ ] SQLAlchemy models have clear domain ownership.
- [ ] Domain routers have clear domain ownership.
- [ ] Application services have clear domain ownership.
- [ ] Repositories have clear domain ownership.
- [ ] `app/api/router.py` is the sole application-level route composition point.
- [ ] Authentication and RBAC remain functional.
- [ ] Alembic metadata and migrations remain functional.
- [ ] Existing API contracts are preserved unless a documented correction is required.
- [ ] Backend tests pass.
- [ ] Frontend tests pass.
- [ ] Frontend build passes.
- [ ] FastAPI starts successfully.
- [ ] No circular imports remain.
- [ ] No duplicate ORM entities remain.
- [ ] No real secrets are committed.
- [ ] The final structure is documented.

---

# 25. Required Final Agent Report

After implementation, report:

1. Files/directories moved.
2. Files/directories removed.
3. Existing functionality preserved.
4. API routes preserved/changed.
5. Database/Alembic changes.
6. Tests executed and results.
7. Any unresolved issues.
8. Final backend tree.
9. Any architectural decisions that required deviation from this specification.

Do not claim completion if tests or startup checks fail.

