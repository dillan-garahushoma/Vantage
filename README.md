# VALORA — property health intelligence for South African private estates

VALORA is a platform for private residential estates (complexes, security estates,
lifestyle estates). It gives an HOA and its residents one place to see how the
estate is actually doing: complaints and their resolution, security incidents,
maintenance work orders, resident ratings, and a single published measure —
the **Living Score** — computed by the backend from that operational history.

The tenant boundary is the **estate**. Every estate-scoped request resolves the
caller's membership first; a client-supplied `estate_id` is never proof of access.

## What is in this repository

```text
backend/    FastAPI modular monolith + async SQLAlchemy + PostgreSQL + Alembic
frontend/   React 19 + Vite + Tailwind (generated API types, no business logic)
docs/       ADRs, the product/architecture documents, the pilot runbook, acceptance evidence
tasks/      the task list, ticked only where there is passing evidence
```

No queues, no microservices, no cloud infrastructure: one API process, one
Postgres, one static frontend. The AI assist layer is optional and off by
default (see [docs/ADR-004-AI-Assist-Layer.md](docs/ADR-004-AI-Assist-Layer.md)).

## Run the demo in three commands

```cmd
cd backend
set DB_NAME=valora_demo
docker compose up -d --build
```

Then seed the demonstration estate (it refuses any database whose name does not
contain `demo`, and it never runs twice):

```cmd
set DATABASE_URL=postgresql+asyncpg://valora_user:valora_password@localhost:5432/valora_demo
set SECRET_KEY=replace-with-a-long-random-development-secret
venv\Scripts\python.exe -m app.cli seed-demo --expect-database valora_demo
```

Open **http://localhost:4173**. The API is on **http://localhost:8000**
(`/docs` for the contract). The first API start takes one to two minutes on a
Windows bind mount — `docker compose ps` reports `healthy` when it is ready.

Full instructions, the demo sign-in table and the switch for a real Gemini key:
[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md). What is deliberately not
built yet: [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md).

## The demo estate

`python -m app.cli seed-demo` creates **one** estate with 120 days of history:
24 units, one HOA administrator, twenty residents, two linked service providers,
three months of complaints across every lifecycle state with matching events,
work orders with resident ratings, security incidents, announcements, five
generated placeholder photographs pushed through the real upload pipeline, and
**real** Living Score snapshots computed by the real engine at several past
dates. No score is ever inserted by hand and no AI output is ever seeded.

| Role | Email | Password |
| --- | --- | --- |
| HOA administrator | `admin@example.com` | `ValoraDemo123!` |
| Resident (owns two units) | `resident01@example.com` | `ValoraDemo123!` |
| Resident | `resident02@example.com` … `resident20@example.com` | `ValoraDemo123!` |
| Service provider (plumbing) | `provider01@example.com` | `ValoraDemo123!` |
| Service provider (electrical) | `provider02@example.com` | `ValoraDemo123!` |
| Investor membership | `investor@example.com` | `ValoraDemo123!` |

The password is the local-only default in `backend/app/seed_demo.py`; set
`VALORA_SEED_PASSWORD` before seeding to choose your own. These accounts exist
**only** in a database whose name contains `demo`.

## Tests

```cmd
cd backend
venv\Scripts\python.exe -m pytest tests -q          :: unit and policy tests
                                                     :: integration tests need TEST_DATABASE_URL
cd ..\frontend
npm run typecheck && npm test                        :: unit and component tests
npm run test:e2e                                     :: browser smoke + responsive sweep, mocked API
npm run test:e2e:live                                :: the live journeys (needs a running app)
```

Integration tests only run against a database whose name contains `test`, and
the demo-seed tests additionally require `demo` — `valora_demo_test_<date>` is
the throwaway that satisfies both. Nothing in the test suite may point at
`valora_db` or a pilot database.

## Status, honestly

- Working end to end: registration and estate registration, the five-step setup
  checklist (description, units, join code, photographs, publish), the public
  directory, joining with a code, complaints → review → assignment → work order →
  completion → resident rating, the Living Score, members, and the AI assist layer
  when it is switched on.
- Verified by tests that pass: see [docs/progress/](docs/progress/) and
  [docs/acceptance/](docs/acceptance/).
- Not built yet: email of any kind (no verification, no emailed password reset —
  the operator CLI is the interim), HTTPS/hosting, automated backups, and a
  malware scan on uploads. The full list is in
  [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md).
