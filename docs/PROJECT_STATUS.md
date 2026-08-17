# VALORA Project Status

This document tracks the ongoing development progress of VALORA, acting as the current source of truth for what has been completed and what is up next.

---

## 🚀 Current Phase: Phase 0 — Foundation ✅ COMPLETE

The goal of Phase 0 is to establish a robust, scalable technical platform before writing any business logic.

### Phase 0 Checklist

- [x] **Step 1: Initialize Project Repository**
  - [x] Create `backend/` root directory
  - [x] Set up Python virtual environment (`venv`)
  - [x] Create domain-driven folder structure per recommended architecture
  - [x] Add initial empty configuration files (`.env`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`)
  - [x] Set up standard `.gitignore`
  - [x] Create basic FastAPI entry point (`app/main.py`)
- [x] **Step 2: Install Core Dependencies**
  - [x] `fastapi`, `uvicorn`
  - [x] `sqlalchemy`, `asyncpg`, `psycopg2-binary` (Database)
  - [x] `alembic` (Migrations)
  - [x] `pydantic-settings`, `pydantic[email]` (Config & validation)
  - [x] `python-jose[cryptography]` (JWT)
  - [x] `passlib[bcrypt]` (Password hashing)
- [x] **Step 3: Configure Environment Variables & Settings**
  - [x] Setup `pydantic-settings` in `app/core/config.py`
  - [x] Define variables for `DATABASE_URL`, `SECRET_KEY`, `ENVIRONMENT`
- [x] **Step 4: Set Up Database & SQLAlchemy**
  - [x] Async SQLAlchemy engine & session maker (`app/db/session.py`)
  - [x] Modern `DeclarativeBase` shared base for all entities
  - [x] `app/db/base.py` — central entity registry for Alembic autogenerate
- [x] **Step 5: Configure Alembic (Database Migrations)**
  - [x] Initialize async Alembic environment
  - [x] Configure `alembic.ini` and `env.py` to auto-detect models (updated to new paths)
- [x] **Step 6: Create the FastAPI App & Logging**
  - [x] Wire up FastAPI app correctly with domain router (`app/api/router.py`)
  - [x] Set up structured logging (`app/core/logging.py`)
- [x] **Step 7: Containerization (Docker)**
  - [x] Configure `Dockerfile` for FastAPI
  - [x] Configure `docker-compose.yml` (PostgreSQL + API services)
- [x] **Step 8: CI/CD Pipeline Setup**
  - [x] Basic GitHub Actions workflow for linting/tests
- [x] **Step 9: Architecture Refactor (Recommended Structure)**
  - [x] Migrated from `app 0/` flat structure to layered domain-driven architecture
  - [x] Created `app/core/` — config, security, logging, exceptions
  - [x] Created `app/db/` — session, base, database helpers
  - [x] Created `app/common/` — enums, pagination, validators
  - [x] Created `app/api/router.py` — top-level API router
  - [x] **identity/** — full layer stack (api, domain/entities, schemas, repositories, services)
  - [x] **property/** — domain entities (Estate, Property, Unit) + layer scaffolds
  - [x] **community/** — domain entities (Announcement, Complaint) + layer scaffolds
  - [x] **providers/** — domain entities (ServiceProvider) + layer scaffolds
  - [x] **analytics/** — domain entities (LivingScore, PropertyValuationSnapshot) + layer scaffolds
  - [x] **ml/** — sub-packages (models, training, inference, preprocessing)
  - [x] Renamed ORM entity files to `entities.py` (distinguishes from ML models)
  - [x] Updated `requirements.txt` with `python-jose`, `passlib`, `pydantic[email]`

---

## 🗺️ Upcoming Phases (From Roadmap)

- [ ] **Phase 1: Authentication & Roles** ← **NEXT UP**
  - [x] JWT token creation & decoding (`app/core/security.py`)
  - [x] Password hashing (`app/core/security.py`)
  - [x] User entity with roles (`app/identity/domain/entities.py`)
  - [x] AuthService: register & login (`app/identity/services/auth_service.py`)
  - [x] Auth API router: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/users/me`
  - [x] Install new dependencies: `pip install python-jose[cryptography] bcrypt pydantic[email]`
  - [x] Run first Alembic migration to create `users` table
  - [ ] Write unit tests for AuthService
  - [x] Add RBAC permission checks (role-based route guards)

- [ ] **Phase 2: Property Domain**
  - [x] Core entities: Estate, Property, Unit (`app/property/domain/entities.py`)
  - [ ] Property schemas, repositories, services, and API router
  - [ ] Alembic migration for property tables
  - [ ] CRUD endpoints for Estate and Unit management

- [ ] **Phase 3: Complaint Management (Core MVP)**
  - [x] Complaint entity (`app/community/domain/entities.py`)
  - [ ] Complaint lifecycle (Create → Review → Assign → Complete → Rate)
  - [ ] Alembic migration for complaints table

- [ ] **Phase 4: Service Providers**
  - [x] ServiceProvider entity (`app/providers/domain/entities.py`)
  - [ ] Provider registration, verification, assignments, and ratings
  - [ ] Alembic migration for service_providers table

- [ ] **Phase 5: HOA Announcements**
  - [x] Announcement entity (`app/community/domain/entities.py`)
  - [ ] Simple CRUD for community announcements

- [ ] **Phase 6: Living Score Engine ⭐**
  - [x] LivingScore entity (`app/analytics/domain/entities.py`)
  - [ ] Rule-based engine calculating estate health scores (`app/analytics/services/living_score_service.py`)

- [ ] **Phase 7: Property Intelligence**
  - [x] PropertyValuationSnapshot entity (`app/analytics/domain/entities.py`)
  - [ ] Connecting Living Score to property valuations

- [ ] **Phase 8: Investor Features**
  - [ ] Insights, ROI (`app/analytics/services/roi_service.py`), property health reports

- [ ] **Phase 9: Dashboards**
  - [ ] Persona-specific views (Resident, HOA, Investor)

- [ ] **Phase 10: Machine Learning**
  - [x] `app/ml/` package scaffold (models, training, inference, preprocessing)
  - [ ] Train ML models on historical data for valuation adjustments and risk scores
  - [ ] `app/ml/inference/` prediction pipelines called by analytics services
