# 4.3 Architectural Design

## 4.3.1 Software Architectural Design

### Architecture Overview
VALORA's target software architecture is a modular, domain-driven, layered system. It is explicitly **not** a Model-View-Controller (MVC) architecture. Instead, VALORA follows a Clean Architecture-inspired pattern in which concerns are separated into distinct, inward-pointing layers: the frontend handles presentation, the API layer handles HTTP routing and security, service classes implement business use cases, repositories abstract data access, and the domain layer contains the core business entities.

This architecture is specifically designed to support VALORA's central product concept: connecting community operational data with property financial intelligence through an analytics layer, so that community health directly informs property valuation.

> **Current implementation alignment:** The technology stack (React frontend, FastAPI backend, SQLAlchemy repositories, PostgreSQL persistence) validates that this architectural pattern is technically feasible and already directionally established. Implementation details are referenced below only to establish feasibility, not to constrain the target design.

### Architectural Layers
The software is organized into the following strict layers, with dependencies pointing inward:
1.  **Presentation Layer (Frontend):** React-based Single Page Application (SPA) providing persona-specific views (Resident, HOA, Investor).
2.  **API Layer:** FastAPI routers that handle HTTP requests, perform input validation via Pydantic schemas, and enforce Role-Based Access Control (RBAC) via JWTs.
3.  **Application/Service Layer:** Orchestrates business use cases (e.g., auth lifecycle, complaint routing, Living Score calculation) and coordinates between domain models and persistence.
4.  **Repository/Data-Access Layer:** Abstracts database interactions using asynchronous SQLAlchemy, ensuring the service layer remains decoupled from SQL specifics.
5.  **Domain/Model Layer:** The core business entities (User, Property, Complaint, LivingScore, AIAnalytic) that define the system's structure.
6.  **Infrastructure Layer:** External concerns such as the PostgreSQL database and ML model execution context.

### Core Software Components
-   **Frontend Application:** Built with React and Vite.
-   **FastAPI Backend:** The core monolith, subdivided into domain-driven modules:
    -   `Identity Module`: Authentication and user management.
    -   `Property Module`: Estate and unit management.
    -   `Community Module`: Complaints, announcements, and maintenance work orders.
    -   `Providers Module`: Service provider registry and reviews.
    -   `Analytics Module`: Translates community operational data (complaint frequency, maintenance resolution times, provider ratings) into the Living Score and property valuation insights. The Living Score entity and data schema are established; the scoring and ML inference services are planned for implementation.
-   **Persistence:** Relational PostgreSQL database managed via Alembic migrations.

### Component Responsibilities
-   **API Layer:** Terminates HTTP connections, translates JSON payloads to internal schemas, and guards endpoints.
-   **Service Layer:** Implements the proprietary logic connecting community health (unresolved complaints, maintenance times) to property health (Living Score).
-   **Analytics Component:** Consumes community operational data to output financial and livability intelligence.

### Dependency Flow
Control flows from the User → Presentation Layer → HTTP/REST API Layer → Service Layer → Repository Layer → Infrastructure/Database.

### Architectural Rationale
The layered architecture ensures that the complex logic calculating property intelligence is entirely decoupled from how data is delivered (HTTP) or stored (SQL). The domain-driven module structure prevents the system from splitting into two disconnected applications (property listing vs. complaint management), enforcing a unified "Property Health" model.

---

## 4.3.2 Hardware Architectural Design

### Target Deployment Architecture
VALORA's target hardware architecture is a cloud-hosted, containerized deployment that separates client devices from application compute and data persistence, with an ingress layer handling public traffic.

```
Users (Web Browsers / Mobile Browsers)
          ↓ HTTPS
     Internet / Public Network
          ↓
  Load Balancer / Ingress
          ↓
  Application Compute
  ├── Frontend Service  (React/Vite SPA served via CDN or container)
  └── API Service       (FastAPI/Uvicorn)
          ↓
  Managed Relational Database  (PostgreSQL)
          +
  Object Storage               (Property images, complaint attachments)
```

### Infrastructure Nodes

| Node | Role | Target Technology |
|---|---|---|
| Client Device | Web browser rendering the SPA | Any modern browser |
| Load Balancer / Ingress | Routes public HTTPS traffic to services | Cloud-managed LB (provider-agnostic) |
| Frontend Service | Serves the React SPA | Container or CDN-hosted static build |
| API Service | Executes FastAPI application logic | Python 3.10+ container |
| Database | Relational persistence, ACID guarantees | PostgreSQL (managed service) |
| Object Storage | Binary asset storage | Cloud object storage |

The choice of cloud provider (AWS, Azure, GCP) is not architecturally significant and is deferred to the deployment planning phase. The containerized packaging ensures portability across providers without changes to application code.

### Infrastructure Responsibilities
-   **Client:** Renders the SPA; holds only ephemeral session state (JWT in memory/localStorage).
-   **Load Balancer:** Terminates TLS, distributes requests, provides a single public entry point.
-   **API Compute:** Executes all business logic, authentication, and data processing. Stateless — can be horizontally scaled.
-   **Database:** Sole source of persistent domain state. Not exposed to the public network.
-   **Object Storage:** Stores binary assets referenced by property listings and complaint records.

### Current Implementation Alignment
The current local development environment uses Docker Compose to mirror this architecture on a single machine:
-   `valora_frontend` container (port 4173) → corresponds to Frontend Service
-   `valora_api` container (port 8000) → corresponds to API Service
-   `valora_db` container (port 5432, PostgreSQL 15) → corresponds to Managed Database
-   `postgres_data` Docker volume → corresponds to persistent storage

This establishes feasibility and ensures environment parity across development machines. The load balancer and object storage nodes are not present in local development; they are production-only concerns.

### Deployment Rationale
Separating compute from persistence allows each tier to be scaled independently. Placing the database on a private internal network (not exposed to the public internet) is the primary security mechanism protecting raw domain data. Object storage decouples binary asset management from the relational database and API, preserving database performance.

---



## 4.3.3 Network Architectural Design

### Network Overview
The network architecture defines communication paths between the decoupled frontend and backend, as well as internal container networking. It relies on standard web protocols and establishes clear security trust boundaries.

### Communication Paths
1.  **User to Frontend:** User interactions occur entirely within the client's browser after the initial asset load.
2.  **Frontend to API (Backend):** The React client communicates with the FastAPI backend via asynchronous REST API calls over HTTP(S).
3.  **API to Database:** The FastAPI backend communicates with the PostgreSQL database container over a dedicated internal Docker network.

### Security Boundaries
-   **External Trust Boundary (Untrusted to Trusted):** The connection between the public Internet (Client) and the API. This boundary is secured by:
    -   JWT (JSON Web Token) bearer authentication for endpoint authorization.
    -   (Proposed) TLS/HTTPS encryption for data in transit.
-   **Internal Trust Boundary (Trusted to Trusted):** The connection between the API container and the Database container.
    -   The database port (5432) is heavily restricted and should not be exposed to the public internet in production.
    -   Communication relies on secure connection strings and internal network routing.

### Protocols
-   **External:** HTTP / HTTPS (REST/JSON).
-   **Internal:** TCP/IP (AsyncPG database driver protocol).

### Network Rationale
The separation of the frontend and API over REST ensures the backend acts as a strict, secure boundary for all business rules and data access. Keeping the database on a private, unexposed network segment protects raw domain data from direct external attack.

---

## 4.3.4 Class Diagram

### Core Classes
-   **User:** Base class for all system personas (Resident, Admin, Investor, Agent).
-   **Property:** Represents a physical real estate unit.
-   **Complaint:** An operational issue reported by a resident affecting community health.
-   **MaintenanceWorkOrder:** The operational response to a complaint, involving a service provider.
-   **ServiceProvider:** Third-party contractor assigned to resolve issues.
-   **AIAnalytic / LivingScoreEntity:** The intelligence layer quantifying the property's health.

### Attributes (Key Examples)
-   **User:** `user_id`, `email`, `role`, `hoa_approved`
-   **Property:** `unit_id`, `unit_no`, `complex_name`
-   **Complaint:** `complaint_id`, `category`, `status`, `is_anonymous`
-   **MaintenanceWorkOrder:** `work_order_id`, `status`, `job_cost`, `resident_rating`
-   **ServiceProvider:** `provider_id`, `trade`, `avg_rating`, `verified`
-   **AIAnalytic:** `analytics_id`, `predicted_market_value`, `growth_score`, `confidence_score`

### Relationships & Multiplicity
-   **User to Complaint (Association):** A User (Resident) logs zero or more Complaints. (1 to 0..*)
-   **Property to Complaint (Association):** A Property is the subject of zero or more Complaints. (1 to 0..*)
-   **Complaint to MaintenanceWorkOrder (Association):** A Complaint may trigger zero or one Work Order. (1 to 0..1)
-   **ServiceProvider to MaintenanceWorkOrder (Association):** A Service Provider executes zero or more Work Orders. (1 to 0..*)
-   **Property to AIAnalytic (Composition):** A Property has generated intelligence/analytics derived from its operational history. (1 to 0..*)

### Responsibilities
The class structure explicitly links operational events to financial outcomes. `Complaint` and `MaintenanceWorkOrder` track the real-time health of the community. `AIAnalytic` is responsible for ingesting this operational history (alongside traditional property data) to generate the Living Score and valuation metrics, fulfilling the system's core product mandate.

### Class Diagram Specification
The entities are derived directly from the SQLAlchemy ORM models implemented in the repository, ensuring complete fidelity to the actual database schema and application domain logic.

---

# Diagram Generation Specification

This section provides precise instructions for the diagram-generation AI to create the four corresponding Draw.io architectural visualisations.

### Diagram 1: `01_VALORA_Software_Architecture`
-   **Purpose:** Show the layered, domain-driven structure (NOT MVC) and the dependency flow from UI to Database.
-   **Nodes/Containers:**
    -   *Presentation Layer:* React Frontend SPA
    -   *API Layer:* FastAPI Routers, JWT Auth Guard
    -   *Application/Service Layer (Grouped):* AuthService, PropertyService, CommunityService, Analytics/LivingScore Engine
    -   *Repository Layer:* SQLAlchemy Repositories
    -   *Domain Layer:* Core Entities (User, Property, Complaint, etc.)
    -   *Infrastructure Layer:* PostgreSQL Database
-   **Relationships:** Top-down directed arrows. Presentation -> API -> Service -> Repository -> Domain. Repository -> Infrastructure.
-   **Labels:** Label arrows with actions (e.g., "HTTP/JSON", "Calls", "Queries").
-   **MUST NOT Include:** Cloud provider logos, load balancers, or MVC terminology (Model/View/Controller).

### Diagram 2: `02_VALORA_Hardware_Architecture`
-   **Purpose:** Illustrate the currently IMPLEMENTED containerized local deployment using Docker.
-   **Nodes/Containers:**
    -   *Client Device:* Web Browser
    -   *Docker Host (Local Machine):* (Large container box)
        -   *Node 1:* `valora_frontend` Container (Port 4173)
        -   *Node 2:* `valora_api` Container (Port 8000)
        -   *Node 3:* `valora_db` Container (Port 5432)
        -   *Node 4:* `postgres_data` Docker Volume
-   **Relationships:** Client -> valora_frontend. valora_frontend -> valora_api. valora_api -> valora_db. valora_db -> postgres_data (Volume mount).
-   **Labels:** Use Docker logos or container icons. Label "IMPLEMENTED Architecture".
-   **MUST NOT Include:** AWS/Azure/GCP specific services (EC2, S3, RDS), as they are proposed, not implemented.

### Diagram 3: `03_VALORA_Network_Architecture`
-   **Purpose:** Define communication protocols and security boundaries.
-   **Nodes/Containers:**
    -   Internet / Public Network
    -   Client Browser
    -   Frontend Application
    -   FastAPI Backend
    -   PostgreSQL Database
-   **Security Boundaries:**
    -   Draw a dashed line box around Frontend & Client labeled "Untrusted Zone".
    -   Draw a solid line box around API and Database labeled "Trusted Internal Network".
-   **Relationships/Protocols:**
    -   Client -> Frontend (HTTPS/HTTP)
    -   Frontend -> API (REST API / JSON / JWT Auth)
    -   API -> Database (TCP/IP / AsyncPG)
-   **MUST NOT Include:** Hardware specs or internal code layers (like Repositories). Focus strictly on nodes and protocols over the wire.

### Diagram 4: `04_VALORA_Class_Diagram`
-   **Purpose:** Detail the core domain models and how community operations link to property analytics.
-   **Nodes (UML Classes):**
    -   `User`: user_id, email, role, full_name
    -   `Property`: unit_id, unit_no, complex_name
    -   `Complaint`: complaint_id, category, status
    -   `MaintenanceWorkOrder`: work_order_id, status, job_cost
    -   `ServiceProvider`: provider_id, trade, avg_rating
    -   `AIAnalytic`: analytics_id, predicted_market_value, growth_score
-   **Relationships (with Direction and Multiplicity):**
    -   User -> Complaint (Association, 1 to 0..*)
    -   Property -> Complaint (Association, 1 to 0..*)
    -   Complaint -> MaintenanceWorkOrder (Association, 1 to 0..1)
    -   ServiceProvider -> MaintenanceWorkOrder (Association, 1 to 0..*)
    -   Property -> AIAnalytic (Composition/Strong Association, 1 to 0..*)
-   **Labels:** Standard UML notation. No methods are strictly required unless specifically identifying a service action; focus on attributes.
-   **MUST NOT Include:** Every single database table (like linking tables) or infrastructure classes (like routers or database sessions). Keep it strictly focused on the business domain.
