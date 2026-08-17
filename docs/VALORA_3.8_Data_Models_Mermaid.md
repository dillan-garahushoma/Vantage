# VALORA — 3.8 Data Modeling for Proposed System (Mermaid → draw.io)

How to use: In draw.io, go to **Extras > Edit Diagram**, paste one code block at a
time (with the ```mermaid fences removed), pick **Mermaid** as the type, and hit
**OK**. Each diagram below is independent — import them onto separate pages.

All fixes from the technical review have been applied and are flagged inline
with `%% FIX #n` comments (remove these comments before final submission if
your supervisor wants clean diagrams).

---

## 1. Context Diagram (Level 0)

```mermaid
flowchart TB
    SYS(("VALORA<br/>Property Intelligence &<br/>Community Management System"))

    Resident["Resident"]
    Investor["Investor"]
    EstateAgent["Estate Agent"]
    CasualVisitor["Casual Visitor"]
    HOAAdmin["HOA Admin"]
    MVR["Municipal Valuation<br/>Registry (external)"]
    ServiceProvider["Service Provider"]

    Resident -- "complaint details, service requests" --> SYS
    SYS -- "complaint status, announcements, basic property data" --> Resident

    Investor -- "valuation / ROI request" --> SYS
    SYS -- "10-yr ROI, valuation, rental yield, complaint trends (read-only)" --> Investor

    %% FIX #1: Estate Agent added as external entity with data flows
    EstateAgent -- "property listing data" --> SYS
    SYS -- "living score" --> EstateAgent

    %% FIX #1: Casual Visitor added as external entity with data flows
    CasualVisitor -- "valuation request" --> SYS
    SYS -- "free valuation estimate, suburb growth score" --> CasualVisitor

    %% FIX #3: HOA Admin now has explicit labeled flows (previously an entity with no flows)
    HOAAdmin -- "verify providers, moderate complaints, post announcements, manage AI training data" --> SYS
    SYS -- "complaint reports, provider applications" --> HOAAdmin

    MVR -- "market & valuation data feed" --> SYS

    ServiceProvider -- "job status, completion notes" --> SYS
    SYS -- "work order assignment" --> ServiceProvider
```

---

## 2. Level 1 Data Flow Diagram

```mermaid
flowchart TB
    Resident["Resident"]
    Investor["Investor"]
    EstateAgent["Estate Agent"]
    CasualVisitor["Casual Visitor"]
    HOAAdmin["HOA Admin"]
    MVR["Municipal Valuation Registry"]
    ServiceProvider["Service Provider"]

    P1(["1.0 Manage Users<br/>& Authentication"])
    P2(["2.0 Property Intelligence<br/>& Valuation"])
    P3(["3.0 Manage Complaints<br/>& Maintenance"])
    P4(["4.0 Manage Service<br/>Provider Directory"])
    P5(["5.0 Manage<br/>Announcements"])

    D1[("D1 Users Registry")]
    D2[("D2 Property & Market Records")]
    D3[("D3 Complaints Log")]
    D4[("D4 Service Providers Directory")]
    D5[("D5 Announcements")]

    Resident --> P1
    P1 --> D1
    D1 --> P1

    Resident -- "valuation request" --> P2
    EstateAgent -- "listing data" --> P2
    CasualVisitor -- "valuation request" --> P2
    Investor -- "ROI / valuation request" --> P2
    MVR -- "market data feed" --> P2
    P2 --> D2
    D2 --> P2
    P2 -- "10-yr ROI, valuation, rental yield" --> Investor
    P2 -- "free estimate, growth score" --> CasualVisitor
    P2 -- "living score" --> EstateAgent
    %% FIX #7: Level 0/1 balancing — Resident now shown receiving basic property data from 2.0
    P2 -- "basic property data" --> Resident

    Resident -- "complaint details" --> P3
    P3 --> D3
    D3 --> P3
    P3 -- "complaint status" --> Resident
    P3 -- "complaint trends (read-only)" --> Investor
    ServiceProvider -- "job status, completion notes" --> P3
    P3 -- "work order assignment" --> ServiceProvider

    HOAAdmin -- "verify / moderate" --> P4
    P4 --> D4
    D4 --> P4
    P4 -- "provider applications" --> HOAAdmin

    %% FIX #2: New process 5.0 Manage Announcements + D5 data store
    HOAAdmin -- "post announcement" --> P5
    P5 --> D5
    D5 --> P5
    P5 -- "announcements" --> Resident

    %% FIX #8: "Levy Parameters" label removed from D2 flow — not in requirements or ERD
```

---

## 3. Entity Relationship Diagram

```mermaid
erDiagram
    roles ||--o{ users : "has"
    users ||--o{ complaints : "logs"
    users ||--o{ announcements : "posts"
    properties ||--o{ complaints : "receives"
    properties ||--o{ ai_analytics : "generates"
    properties ||--o{ historical_market_data : "tracks"
    complaints ||--o{ maintenance_work_orders : "triggers"
    service_providers ||--o{ maintenance_work_orders : "assigned_to"

    roles {
        int role_id PK
        varchar role_name
    }

    users {
        int user_id PK
        int role_id FK
        varchar full_name
        varchar email
        varchar password_hash
    }

    properties {
        int property_id PK
        varchar ref_number
        varchar unit_number
        varchar complex_name
        varchar street_address
        varchar suburb
        int size_sqm
    }

    historical_market_data {
        int market_data_id PK
        int property_id FK
        varchar record_source
        numeric valuation_amount
        date record_date
    }

    ai_analytics {
        int analytics_id PK
        int property_id FK
        numeric predicted_market_value
        numeric rental_yield_pct
        numeric growth_score
        numeric ten_year_roi_estimate
        numeric living_score
        timestamp calculated_at
    }

    service_providers {
        int provider_id PK
        varchar business_name
        varchar core_specialization
        boolean is_hoa_verified
        numeric average_rating
    }

    complaints {
        int complaint_id PK
        int user_id FK
        int property_id FK
        varchar category
        text description
        varchar current_status
        timestamp created_at
    }

    maintenance_work_orders {
        int work_order_id PK
        int complaint_id FK
        int provider_id FK
        timestamptz assigned_at
        timestamptz resolved_at
        numeric job_cost
        numeric resident_rating
        text completion_notes
    }

    announcements {
        int announcement_id PK
        int user_id FK
        varchar title
        text body
        timestamp posted_at
        boolean is_active
    }
```

**Fixes applied to the ERD:**
- `announcements` entity added (FIX #2), linked to `users` via `posts`
- `historical_market_data` cardinality corrected from `||--|{` to `||--o{` (FIX #4) — a property can have zero historical market records, not mandatory one-or-more
- `living_score` attribute added to `ai_analytics` (FIX #5)
- `created_at` timestamp added to `complaints` (FIX #6)

---

## 4. State Transition Diagram (Complaint Lifecycle)

```mermaid
stateDiagram-v2
    [*] --> Logged : resident submits complaint
    Logged --> UnderReview : HOA Admin reviews
    UnderReview --> Rejected : does not meet criteria
    UnderReview --> Assigned : provider assigned (work order created)
    Assigned --> InProgress : provider starts job
    InProgress --> Resolved : provider marks complete
    Resolved --> Closed : resident confirms / rating given
    Resolved --> Reopened : resident disputes resolution
    Reopened --> Assigned : reassigned to provider
    Rejected --> [*]
    Closed --> [*]
```

---

## 5. Use Case Diagram

Mermaid has no native UML use-case notation, so this is modeled as a
flowchart (actors as stadium shapes, use cases as rounded rectangles). This
imports into draw.io fine as a diagram; relabel shapes with the UML actor
stick-figure style in draw.io afterward if your supervisor wants strict UML.

```mermaid
flowchart LR
    subgraph Actors
        Resident(["Resident"])
        Investor(["Investor"])
        EstateAgent(["Estate Agent"])
        CasualVisitor(["Casual Visitor"])
        HOAAdmin(["HOA Admin"])
    end

    subgraph "VALORA System"
        UC1(Report Complaint)
        UC2(Track Complaint Status)
        UC3(Find Service Provider)
        UC4(View Basic Property Data)
        UC5(View 10-yr ROI & Valuation)
        UC6(View Complaint Trends)
        UC7(List Property)
        UC8(View Living Score)
        UC9(Get Free Valuation Estimate)
        UC10(View Suburb Growth Score)
        UC11(Verify Service Provider)
        UC12(Moderate Complaints)
        UC13(Post Announcement)
        UC14(Manage AI Training Data)
    end

    Resident --> UC1
    Resident --> UC2
    Resident --> UC3
    Resident --> UC4

    Investor --> UC5
    Investor --> UC6

    EstateAgent --> UC7
    EstateAgent --> UC8

    CasualVisitor --> UC9
    CasualVisitor --> UC10

    HOAAdmin --> UC11
    HOAAdmin --> UC12
    HOAAdmin --> UC13
    HOAAdmin --> UC14
```

---

## Summary of fixes applied (cross-reference to technical review)

| # | Fix | Diagram(s) |
|---|-----|-----------|
| 1 | Added Estate Agent & Casual Visitor as external entities with flows | Context, Level 1 DFD, Use Case |
| 2 | Added `announcements` entity, D5 data store, 5.0 process, HOA Admin flows | Context, Level 1 DFD, ERD, Use Case |
| 3 | Added labeled HOA Admin flows (previously entity with no flows) | Context |
| 4 | Fixed `properties`–`historical_market_data` cardinality to `||--o{` | ERD |
| 5 | Added `living_score` to `ai_analytics` | ERD |
| 6 | Added `created_at` to `complaints` | ERD |
| 7 | Fixed Level 0/1 balancing — Resident now receives basic property data from 2.0 | Level 1 DFD |
| 8 | Removed "Levy Parameters" label (not in requirements or ERD) | Level 1 DFD |
