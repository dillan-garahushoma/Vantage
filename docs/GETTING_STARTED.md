# GETTING STARTED — from a clean checkout to a working demo

Every command below is for **Windows `cmd.exe`** and is run from the repository
root unless the line says otherwise. There are two ways to run VALORA: the whole
stack in Docker (quickest, what a demonstration uses) or the API on the host with
Docker providing only Postgres (what development uses). Both are here.

Nothing in this document has been invented: the commands marked **verified** were
run against this checkout and their results are recorded in
[docs/progress/onb-master.md](progress/onb-master.md).

---

## 1. Start Docker Desktop

```cmd
:: Docker Desktop must be running before anything below.
:: If it is not, start it from the Start menu and wait for "Engine running".
docker version
```

If `docker version` hangs or reports a pipe error, Docker Desktop is still
starting (or has been shut down) — start it and wait.

## 2. Run the whole stack in Docker (verified)

```cmd
cd backend
set DB_NAME=valora_demo
docker compose up -d --build
```

This builds the API image and the frontend image, creates Postgres with the
volume `postgres_data`, starts the API (which runs `alembic upgrade head` itself,
then uvicorn) and serves the built frontend with nginx.

```cmd
docker compose ps
```

Expect three containers and, after roughly one to two minutes on a Windows bind
mount, this:

```text
backend-api-1        running   healthy    Up ... (healthy)
backend-db-1         running              Up ...
backend-frontend-1   running   healthy    Up ... (healthy)
```

Then open:

- **http://localhost:4173** — the app
- **http://localhost:8000/docs** — the API contract
- `curl http://localhost:8000/health` — `{"status":"ok"}` when the API is ready

`docker compose down` stops the stack; the database volume and `backend/uploads/`
survive. Only a manual delete removes them.

To bring the *next* demonstration up against a **fresh** database, set a new
`DB_NAME` (for example `DB_NAME=valora_demo2`) — the seeder below refuses to run
against anything that is not clearly a demo database.

## 3. Seed the demonstration estate (verified)

The seeder is guarded and idempotent: it refuses any database whose name does not
contain `demo`, refuses a database that is not the one you name, and reports
"already exists — nothing changed" on a second run.

```cmd
cd backend
set DATABASE_URL=postgresql+asyncpg://valora_user:valora_password@localhost:5432/valora_demo
set SECRET_KEY=replace-with-a-long-random-development-secret
venv\Scripts\python.exe -m app.cli seed-demo --expect-database valora_demo
```

It prints one summary and the sign-in table **once** — a password value is never
printed. The accounts are:

| Role | Email | Password |
| --- | --- | --- |
| HOA administrator | `admin@example.com` | `ValoraDemo123!` |
| Resident (owns two units) | `resident01@example.com` | `ValoraDemo123!` |
| Residents | `resident02@example.com` … `resident20@example.com` | `ValoraDemo123!` |
| Service provider (plumbing) | `provider01@example.com` | `ValoraDemo123!` |
| Service provider (electrical) | `provider02@example.com` | `ValoraDemo123!` |
| Investor membership | `investor@example.com` | `ValoraDemo123!` |

`ValoraDemo123!` is the local-only default. Set `VALORA_SEED_PASSWORD` before
seeding to use your own (it is never stored in the repository or printed).
**These accounts are valid in a demo database only** — the seeder will not write
to a pilot or production database, and you should not reuse the password there.

The seed creates 24 units, 20 residents, 2 providers, 3 months of complaints in
every state (with the events each transition implies), work orders with resident
ratings, 6 security incidents, 5 announcements, 5 placeholder photographs through
the **real** upload pipeline, and **real** Living Score snapshots at four past
`as_of` dates. No AI output is seeded, ever.

Recompute the score later (a scheduled-job path, one snapshot per estate):

```cmd
venv\Scripts\python.exe -m app.cli recalc-living-scores --include-demo
```

## 4. Or: the API on the host, Postgres in Docker (development)

```cmd
cd backend
:: 1. Postgres only
docker compose up -d db

:: 2. The environment file (never commit a real .env)
copy .env.example .env

:: 3. Migrate, then start the API
venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

In a second terminal, run the frontend against that API:

```cmd
cd frontend
set VITE_API_BASE_URL=http://127.0.0.1:8000
npm install
npm run dev
```

Open **http://localhost:5173**. `CORS_ORIGINS` already lists 5173 and 4173, so
either frontend can talk to the API.

Useful checks before you start the API:

```cmd
venv\Scripts\python.exe -m alembic -c alembic.ini heads          :: must print exactly one head
venv\Scripts\python.exe -m alembic -c alembic.ini current
```

## 5. Run the tests

```cmd
cd backend
venv\Scripts\python.exe -m pytest tests -q
```

Without `TEST_DATABASE_URL` the integration tests **skip** (and the run says so);
unit and policy tests still pass. To run everything, create a throwaway database
whose name contains `test` and point the suite at it:

```cmd
:: create the throwaway (never point this at valora_db or a pilot database)
docker exec backend-db-1 psql -U valora_user -d postgres -c "CREATE DATABASE valora_demo_test_20261012;"

set TEST_DATABASE_URL=postgresql+asyncpg://valora_user:valora_password@localhost:5432/valora_demo_test_20261012
venv\Scripts\python.exe -m pytest tests -q
```

The demo-seed tests additionally require `demo` in the database name, which is
why `valora_demo_test_<date>` satisfies both guards. Drop the throwaway when you
are finished:

```cmd
docker exec backend-db-1 psql -U valora_user -d postgres -c "DROP DATABASE valora_demo_test_20261012;"
```

Frontend:

```cmd
cd frontend
npm run typecheck
npm test                  :: vitest, jsdom
npm run test:e2e          :: Playwright smoke + responsive sweep, needs no API
```

The live journeys drive a **running** app and a seeded database. Point them at
whatever pair you are running — the configuration starts no server, so a stale
pair can never be used silently:

```cmd
set E2E_BASE_URL=http://localhost:4173
npm run test:e2e:live
```

## 6. Switch on real Gemini (demonstration database only)

The AI layer is optional and **off** by default; the product works with it off
(that is tested). To let the demo estate use a real provider, set these in the
environment the API runs in (or in `backend/.env`) and restart the API:

```cmd
set AI_ENABLED=true
set AI_PROVIDER=gemini
set AI_MODEL=<a Gemini model your key can call>
set GEMINI_API_KEY=<your key - never commit it, never paste it into a file in git>
set AI_INSIGHTS_ENABLED=true
set AI_TIMEOUT_SECONDS=75
```

- With `AI_PROVIDER=gemini` a key is **required**; configuration refuses to start
  without it. `AI_PROVIDER=fake` is a deterministic in-process stand-in and is
  refused outside `development`/`test` — it is what the automated tests use.
- **Triage** also needs `AI_TRIAGE_ENABLED=true` **and**
  `AI_PERSONAL_DATA_ALLOWED=true`, because a complaint contains a person's words.
  A triage request without that second opt-in is refused with the reason `policy`
  and the UI says suggestions are unavailable.
- **Keep triage off for real residents** until the AI checklist in
  [docs/PILOT_RUNBOOK.md](PILOT_RUNBOOK.md) has been worked through: that is the
  POPIA trail for sending personal data to a third party.
- Per-estate cost control is built in: `AI_DAILY_CALL_CAP_PER_ESTATE` (default
  200/day) against the append-only `ai_call_events` ledger. A refused call is
  recorded, and no prompt or output is ever logged.

A Gemini smoke check previously succeeded for both feature flags, but a later
request hit the free-tier 429 quota. The full health brief was not re-verified
against Gemini after the output-budget fix. A timeout of 75 seconds is the current
default because one measured brief took 55 seconds; an explicit environment
setting overrides that default. Real-provider availability still depends on the
selected model and the key's current quota.

## 7. Recover a locked-out account (no email yet)

There is no email transport in this build, so there is no "forgot password"
email. The operator path is a script that prints a new password once:

```cmd
cd backend
:: DRY RUN by default - prints the target database and what it would do
venv\Scripts\python.exe scripts\reset_password.py --email admin@example.com --expect-database valora_demo

:: then, when you are sure
venv\Scripts\python.exe scripts\reset_password.py --email admin@example.com --expect-database valora_demo --apply
```

The generated password is printed once, stored only as a bcrypt hash, and never
logged.

## 8. Where the rest of the answers live

| Question | Document |
| --- | --- |
| Why is the estate the tenant? | [ADR-001](ADR-001-Estate-Tenancy.md), [ADR-002](ADR-002-estate-authorization.md) |
| How do roles and joining work? | [ADR-006](ADR-006-role-scoped-onboarding.md), [ADR-007](ADR-007-estate-join-codes-and-self-service-membership.md) |
| Who may compute a score? | [ADR-005](ADR-005-Living-Score-Authority.md), [LIVING_SCORE_V1.md](LIVING_SCORE_V1.md) |
| The AI layer's rules | [ADR-004](ADR-004-AI-Assist-Layer.md) |
| Taking this to a real estate | [PILOT_RUNBOOK.md](PILOT_RUNBOOK.md) |
| What is not built | [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) |
| What was verified, and how | [docs/progress/](progress/), [docs/acceptance/](acceptance/) |
