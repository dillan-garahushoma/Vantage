# VALORA — Section 4.3 Architectural Design: Architecture Audit & Authoritative Specification

## Role

Act as the **Software Architect and Systems Design Lead** for VALORA.

Your job is **not to produce attractive generic architecture prose**. Your job is to inspect the actual VALORA repository and existing project documentation, identify inaccuracies in the current Section 4.3 draft, resolve them against the implementation and approved system concept, and produce an authoritative technical specification for Section 4.3.

This specification will later be handed to another AI whose only job is to create the final Draw.io visualisations. Therefore, architectural consistency is more important than visual presentation.

---

## Primary Goal

Produce a technically defensible **Section 4.3 — Architectural Design** covering:

1. **4.3.1 Software Architectural Design**
2. **4.3.2 Hardware Architectural Design**
3. **4.3.3 Network Architectural Design**
4. **4.3.4 Class Diagram**

The four sections must describe the **same system** from four different architectural perspectives.

Do not simply rewrite the existing DOCX. Audit it first.

---

# 1. Mandatory Repository Investigation

Before changing the architecture, inspect the actual project.

At minimum, inspect:

### Backend
- complete backend directory structure
- FastAPI application entry point
- API/router structure
- services/application layer
- repositories/data-access layer
- domain/model layer
- database configuration
- SQLAlchemy configuration
- Alembic configuration/migrations
- authentication implementation
- schemas/Pydantic models
- AI/analytics implementation, if present
- Docker configuration
- environment/configuration files

### Frontend
- application structure
- major pages/features
- API communication
- authentication flow
- major domain-facing modules

### Infrastructure
- Dockerfiles
- docker-compose configuration
- database container/configuration
- environment configuration
- any deployment configuration actually present

### Existing analysis/design documentation
Inspect the existing:
- ERD/data model
- DFD
- use cases/personas
- requirements
- previous architectural design
- project concept documentation

Use the actual repository as the source of truth for **implemented architecture**.

---

# 2. Critical Corrections to the Existing Draft

The current architectural design draft contains several assumptions that must NOT automatically be carried forward.

## A. Do NOT incorrectly label the backend as MVC

The previous draft states that VALORA uses:

> "Client-Server architecture based on the Model-View-Controller (MVC) pattern"

Do not retain MVC unless the actual implementation clearly demonstrates a conventional MVC architecture.

The current architectural direction is better represented as a layered / Clean Architecture-inspired structure:

**Presentation/API → Application/Services → Data Access/Repositories → Domain/Models → Infrastructure**

Use the terminology that accurately matches the repository.

The architecture should make clear why separation exists:
- API layer handles HTTP/API concerns
- service/application layer handles use cases and business logic
- repositories handle persistence/data access
- domain/models represent core business concepts
- infrastructure handles database/external technical concerns

Do not invent layers that do not exist.

---

## B. Do NOT present hypothetical AWS infrastructure as already implemented

The previous draft mentions:
- AWS EC2
- AWS ECS
- Azure VMs
- AWS RDS
- AWS S3
- Multi-AZ
- VPC
- auto-scaling
- cloud load balancer

These are plausible production technologies, but they must NOT be represented as current implementation unless the repository actually contains evidence of them.

Clearly distinguish:

### Implemented/current architecture
What VALORA currently runs on and what exists in the repository.

### Proposed production deployment
Infrastructure that could reasonably be used when deploying VALORA for production.

If a production deployment architecture is included, explicitly label it as **proposed** rather than pretending it already exists.

Do not choose AWS/Azure/GCP merely because it sounds professional.

---

## C. Correct the network architecture

Do not automatically draw a load balancer distributing traffic to both a React frontend and FastAPI backend.

Determine from the actual project/deployment model how the frontend and API are intended to communicate.

The network architecture must accurately show:

**User → Frontend → REST/HTTPS API → FastAPI → persistence/services**

and any genuine external integrations.

Identify security/trust boundaries where appropriate.

Do not introduce:
- API gateways
- reverse proxies
- CDNs
- load balancers
- firewalls
- private subnets

unless they are either implemented or explicitly identified as proposed production infrastructure.

---

## D. Do not turn the class diagram into a disguised ERD

The class diagram must be based on the actual domain model and software responsibilities.

Inspect the actual models and relationships.

Do not assume relationships simply because they sound logical.

For every important relationship, establish:
- class A
- relationship
- class B
- cardinality/multiplicity
- whether it is inheritance, association, aggregation or composition
- relevant attributes
- relevant responsibilities/methods where justified

Do not add methods merely to make the diagram look like UML.

Do not add classes merely to make the diagram larger.

The class diagram should represent the software/domain structure, not every database column.

---

# 3. Preserve VALORA's Actual Product Concept

VALORA is not simply:
- a property valuation application, plus
- a complaint-management application.

The approved system concept connects property financial intelligence with community operational health.

The architectural design must preserve the relationship:

**Property/community operational data → analytics → living/property health indicators → property intelligence/valuation**

Complaint trends, resolution performance, ratings and related operational data are important because they can provide signals about the health/livability of a property/community.

Do not treat AI analytics as a decorative standalone feature.

If the current implementation does not yet fully implement this relationship, clearly distinguish:
- implemented functionality
- intended/target functionality

Do not falsely claim that an AI model exists if it does not.

---

# 4. Produce the Four Architectural Views

## 4.3.1 Software Architectural Design

Describe the actual software architecture.

Include:

- frontend/presentation
- API layer
- application/service layer
- repository/data-access layer
- domain/model layer
- infrastructure
- database
- authentication
- AI/analytics where applicable
- major functional modules

Explain the dependency direction.

The software architecture should answer:

> How is VALORA internally organised, and how do its components collaborate?

The final visual must be a **software/component/layer architecture diagram**, NOT a DFD.

---

## 4.3.2 Hardware Architectural Design

Describe the infrastructure required to execute VALORA.

Separate:

### Current/implemented infrastructure
What the project currently uses, including Docker and local development infrastructure where relevant.

### Proposed production infrastructure
Only if useful and clearly labelled.

The hardware/deployment view should answer:

> What computing infrastructure hosts the VALORA components?

Do not waste the diagram on CPU/RAM specifications unless technically relevant.

Focus on:
- client devices
- application compute
- database infrastructure
- storage
- relevant supporting infrastructure

---

## 4.3.3 Network Architectural Design

Describe communication paths and security boundaries.

Show:
- client
- internet/network
- frontend
- API
- backend services
- database
- external services/data sources where applicable

Identify:
- HTTPS
- REST/JSON
- authentication mechanism
- database connectivity
- public/private boundaries if actually applicable

The network view should answer:

> How does information travel through VALORA and where are the security boundaries?

Do not duplicate the software architecture.

---

## 4.3.4 Class Diagram

Derive the class diagram from:
1. actual code/models
2. approved data model
3. system requirements/use cases

Include the core domain classes and their meaningful relationships.

The class diagram should answer:

> What are the principal objects in the VALORA system, what do they represent, and how are they related?

Validate every multiplicity against the repository/data model.

---

# 5. Consistency Requirements

The four views MUST agree.

For example:

If the class diagram contains `Complaint`, then:
- the software architecture should contain the complaint-management capability;
- the database/data-access architecture should account for complaint persistence;
- the network architecture should account for requests involving complaint management.

If the architecture contains an AI analytics component, identify:
- its inputs
- its outputs
- where it executes
- what data it depends on
- whether it is implemented or proposed

No diagram may contain components that have no corresponding architectural justification.

---

# 6. Current vs Proposed Architecture

Use explicit labels wherever necessary:

**IMPLEMENTED**

for functionality/infrastructure verified in the repository.

**PROPOSED**

for production infrastructure or capabilities that are design recommendations rather than current implementation.

**CONCEPTUAL**

for approved domain/system concepts that are part of the intended system but not yet implemented.

Never silently convert a proposed design into a claim about the current implementation.

---

# 7. Required Final Output

Produce a polished Markdown document:

`VALORA_4.3_ARCHITECTURAL_DESIGN.md`

Structure:

# 4.3 Architectural Design

## 4.3.1 Software Architectural Design
### Architecture Overview
### Architectural Layers
### Core Software Components
### Component Responsibilities
### Dependency Flow
### Architectural Rationale

## 4.3.2 Hardware Architectural Design
### Current Infrastructure
### Proposed Production Infrastructure
### Infrastructure Responsibilities
### Deployment Rationale

## 4.3.3 Network Architectural Design
### Network Overview
### Communication Paths
### Security Boundaries
### Protocols
### Network Rationale

## 4.3.4 Class Diagram
### Core Classes
### Attributes
### Relationships
### Multiplicity
### Responsibilities
### Class Diagram Specification

---

# 8. Diagram Specification for the Next AI

At the end of the document, create a section:

# Diagram Generation Specification

Provide precise instructions/data for a diagram-generation specialist.

Define exactly four diagrams:

1. `01_VALORA_Software_Architecture`
2. `02_VALORA_Hardware_Architecture`
3. `03_VALORA_Network_Architecture`
4. `04_VALORA_Class_Diagram`

For EACH diagram provide:

- diagram purpose
- nodes/components
- labels
- relationships
- relationship direction
- protocols where applicable
- grouping/containers
- security boundaries where applicable
- multiplicities for UML
- elements that MUST NOT be included
- current/proposed/conceptual status

The next AI should be able to create the Draw.io diagrams from this specification without having to infer the architecture.

---

# 9. Quality-Control Checklist

Before finalising the document, verify:

- [ ] MVC is not claimed without implementation evidence.
- [ ] The actual backend architecture is accurately represented.
- [ ] Current Docker architecture is represented accurately.
- [ ] Hypothetical cloud services are not presented as implemented.
- [ ] Current vs proposed infrastructure is explicitly separated.
- [ ] Network architecture does not contain invented infrastructure.
- [ ] Class relationships are validated against the actual system.
- [ ] The class diagram is not simply an ERD.
- [ ] AI/analytics is represented according to actual implementation.
- [ ] The property-health/community-data relationship is architecturally acknowledged.
- [ ] All four views describe the same system.
- [ ] The existing DFD is not duplicated as an architecture diagram.
- [ ] No unsupported technology or component has been invented.
- [ ] The final diagram specification is precise enough for another AI to create Draw.io files.

---

## Final instruction

Do not optimise for sounding sophisticated.

Optimise for **technical accuracy, traceability to the actual VALORA repository, architectural coherence, and academic defensibility**.

Where the existing draft is wrong, correct it.

Where the repository does not provide enough evidence, explicitly state the uncertainty instead of inventing an answer.

The output of this task is the authoritative architectural specification that will be handed to a separate diagram-generation AI.
