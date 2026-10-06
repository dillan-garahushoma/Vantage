---
name: valora-architecture
description: Enforces VALORA's modular monolith and Clean/Layered architecture boundaries across backend and frontend. Use when adding or refactoring endpoints, services, repositories, or frontend state.
---

# VALORA Architecture Standards

VALORA is a **modular monolith** following a Clean/Layered architecture. It is explicitly **not** an MVC pattern.

## Strict Layer Hierarchy & Dependency Direction

Dependencies point strictly inward:

```text
Presentation Layer (React SPA)
       ↓  HTTP / REST JSON + Bearer JWT
API Layer (FastAPI Routers + Pydantic DTOs)
       ↓  Calls application use cases
Application / Service Layer (Business Logic & Orchestration)
       ↓  Invokes data access abstractions
Repository Layer (Async SQLAlchemy Data Access)
       ↓  Maps to database models
Domain Layer (Core Entities & Invariants)
       ↓
Infrastructure / Database (PostgreSQL / AsyncPG)
```

## Mandatory Architectural Invariants

1. **No Direct Database Access in API Routers:**
   - Routers (`app/*/api/`) must **never** import `AsyncSession` to execute raw queries or interact with SQLAlchemy models directly.
   - Routers only parse HTTP requests, validate DTO schemas, extract auth tokens/principals, invoke service methods, and return response DTOs.

2. **No Business Logic in Repositories:**
   - Repositories (`app/*/repositories/`) only perform data retrieval, filtering, pagination, and persistence operations.
   - Domain validation, state transitions, scoring, and cross-entity workflows belong exclusively in the service layer (`app/*/services/`).

3. **No Business Logic in React Frontend:**
   - The React frontend is strictly a presentation and interaction layer.
   - Calculations (e.g. Living Score formulas, fee valuations, risk ratings) must never be re-implemented or calculated in client-side JavaScript. The client displays data provided by backend API contracts.

4. **Domain Independence:**
   - Domain entities (`app/*/domain/entities.py`) define identity and core relations. They must not depend on HTTP routers, request schemas, or external transport protocols.

5. **Cross-Domain Boundaries:**
   - Modules (`identity`, `property`, `community`, `providers`, `analytics`) communicate via explicit service interfaces or shared IDs, avoiding circular package dependencies.
