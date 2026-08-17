# VALORA Development Roadmap

## Philosophy

Build **business capabilities**, not screens. Every phase should produce a complete slice of business value before moving to the next.

---

# Phase 0 — Foundation

Establish the technical platform:

- FastAPI project structure
- PostgreSQL
- SQLAlchemy
- Alembic
- Docker
- Environment configuration
- Logging
- CI/CD

Suggested structure:

```text
backend/
    app/
        api/
        core/
        db/
        models/
        repositories/
        services/
        schemas/
        security/
        analytics/
```

---

# Phase 1 — Authentication & Roles

Implement:

- Registration
- Login
- JWT authentication
- Password hashing
- Role-Based Access Control (RBAC)

Roles:

- Resident
- HOA Admin
- Service Provider
- Investor
- Estate Agent

Goal: Every request knows **who** is calling and **what they are allowed to do**.

---

# Phase 2 — Property Domain

Create the core entities:

- Estate
- Property
- Unit
- User
- Role

Relationship:

```text
Estate
   ↓
Properties
   ↓
Units
   ↓
Residents / Owners
```

---

# Phase 3 — Complaint Management (Core MVP)

Implement the complete complaint lifecycle:

```text
Resident
    ↓
Create Complaint
    ↓
HOA Review
    ↓
Assign Provider
    ↓
Provider Completes
    ↓
Resident Rates
    ↓
Closed
```

Database:

- Complaint
- ComplaintStatus
- WorkOrder
- ComplaintImage

Core APIs:

- POST /complaints
- GET /complaints
- PATCH /complaints/{id}
- Assign Provider
- Close Complaint

---

# Phase 4 — Service Providers

Implement:

- Provider registration
- HOA verification
- Assignment
- Ratings

Entities:

- Provider
- ProviderRating
- WorkOrder

---

# Phase 5 — HOA Announcements

Simple CRUD for:

- Create announcement
- Update announcement
- Archive announcement
- Resident read view

---

# Phase 6 — Living Score Engine ⭐

This is VALORA's differentiator.

Inputs:

- Complaint Resolution Time (30%)
- Complaint Frequency (25%)
- Provider Ratings (20%)
- Resident Satisfaction (15%)
- Announcement Activity (10%)

Suggested module:

```text
analytics/
    living_score_engine.py
```

Start with a deterministic rules engine.

---

# Phase 7 — Property Intelligence

Connect:

```text
Property
    ↓
Living Score
    ↓
Valuation
```

Initially use rule-based valuation adjustments.

Replace with ML later.

---

# Phase 8 — Investor Features

Implement:

- Property valuation
- Property Health
- Investment insights
- ROI
- Rental yield
- Growth projections

---

# Phase 9 — Dashboards

Resident:

- Open complaints
- Complaint history
- Announcements
- Living Score

HOA:

- Complaint queue
- Average resolution time
- Provider ratings
- Estate health

Investor:

- Valuation
- Living Score
- Property Health
- Investment reports

---

# Phase 10 — Machine Learning

Only after sufficient historical data exists.

Pipeline:

```text
Historical Complaints
        ↓
Historical Living Scores
        ↓
Historical Sales
        ↓
Train ML Model
```

---

# Overall Dependency Graph

```text
Infrastructure
        │
        ▼
Authentication
        │
        ▼
Users & Roles
        │
        ▼
Estates & Properties
        │
        ▼
Complaint Management
        │
        ▼
Work Orders
        │
        ▼
Service Providers
        │
        ▼
Announcements
        │
        ▼
Living Score Engine
        │
        ▼
Property Intelligence
        │
        ▼
Investor Insights
        │
        ▼
Dashboards
        │
        ▼
Machine Learning
```

---

# Recommended Domain Structure

```text
app/
├── identity/          # Authentication, users, roles
├── property/          # Estates, properties, valuations
├── community/         # Complaints, announcements, work orders
├── providers/         # Service providers and ratings
├── analytics/         # Living Score, Property Health, future ML
├── shared/            # Common utilities
└── api/               # HTTP routing
```

## Guiding Principle

Every completed phase should produce a deployable, testable increment that moves VALORA closer to its core objective:

> **Measure and improve Property Health Intelligence for private residential communities.**
