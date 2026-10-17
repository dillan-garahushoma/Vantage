# Test estate — Amberfield Valley (fictional), provisioned by dry run only

Session: 2026-10-11. Branch `valora-work`. **Nothing was written to any database, no migration was
applied, `--apply` was never used, and `app/seed_demo.py` was not touched.** Nothing was committed.

Created: [`backend/pilot/estate.test.json`](../backend/pilot/estate.test.json).

## The file

Read against `scripts/provision_estate.py`'s documented format and validated by the script itself:

| Field | Value |
| --- | --- |
| Estate | `Amberfield Valley`, `is_demo=false`, suburb Westville, city Durban, province KwaZulu-Natal |
| Units | 12: `AMB-01` … `AMB-12` (one shared complex name/street, varying size/bedrooms/bathrooms) |
| HOA admins | 1: `amberfield.hoa.admin@example.test` |
| Service providers | 1: `amberfield.provider.plumbing@example.test`, trade `plumbing`, emergency available |

Every email uses the reserved `.test` domain, the description says the complex is fictional, and no
value in the file belongs to a real person or property.

## What ran (and what it printed)

Both runs were read-only dry runs (`--apply` was not passed).

**1. Against the local development database, `valora_db` — blocked, exit 1.**

```text
Target database: localhost:5432/valora_db
(credentials come from DATABASE_URL and are not shown)
...
sqlalchemy.exc.ProgrammingError: (asyncpg.exceptions.UndefinedTableError)
  relation "estates" does not exist
[SQL: SELECT estates.estate_id, estates.name, ... FROM estates]
```

`valora_db` exists but is **not migrated**: 14 tables, no `estates`, no `estate_memberships`, no
`estate_access`-era tables. It sits at alembic revision `103dd39ca30e`, while the repo head is
`d9f2a4c7e1b3`. Its tables (`listings`, `sales`, `ai_analytics`, `sessions`, `properties`, `reviews`)
look like an early schema from before the estate tenancy work. `103dd39ca30e` **is** in the repo's
migration history, so `alembic upgrade head` should carry it forward — untested, see below.

**2. Against a migrated database, to prove the file and show the plan — exit 0.**

I could not plan against `valora_db` (no schema to read), so I ran the same dry run against
`valora_ai5_wiring`, the throwaway database this machine already had at head from the AI-5 wiring
check. It writes nothing either way:

```text
Target database: localhost:5432/valora_ai5_wiring
(credentials come from DATABASE_URL and are not shown)
Estate to create: Amberfield Valley (is_demo=false)
Units to create (12): AMB-01, AMB-02, AMB-03, AMB-04, AMB-05, AMB-06, AMB-07, AMB-08, AMB-09, AMB-10, AMB-11, AMB-12
HOA admins to create (1): amberfield.hoa.admin@example.test
Service providers to create (1): amberfield.provider.plumbing@example.test (plumbing)
Memberships to create: amberfield.hoa.admin@example.test -> hoa_admin, amberfield.provider.plumbing@example.test -> service_provider

[dry-run] no changes were written. Re-run with --apply to write.
```

Exit code 0. The file parses, the unit numbers do not collide with anything, and the plan is exactly
one estate + 12 units + 1 admin + 1 provider + 2 memberships.

## How to tell which database the script will target

The script **never reads `.env`** — `target_database_url()` reads `DATABASE_URL` from the process
environment only, deliberately, so that the database it prints is provably the database it will
touch. Consequences on Windows:

1. Every run prints its target first: `Target database: host:port/name`, with the password redacted.
   **Read that line before you read anything else.** If it is not the database you meant, stop.
2. If `DATABASE_URL` is not set in *that* cmd session, the run fails with an error rather than
   guessing. Check what the session holds with `set DATABASE_URL` (prints the current value; prints
   `Environment variable DATABASE_URL not defined` if unset).
3. The API *does* read `backend\.env`, so the script's target and `backend\.env`'s `DATABASE_URL` must
   be the same database for the app to see the new estate. Set them to the same value.
4. `--expect-database valora_db` is a typed guard: the run refuses unless the target's file name is
   exactly that. It is the cheapest protection against the one mistake that cannot be undone. Never
   add `--allow-demo-database` for a database you care about.
5. `DATABASE_URL` contains the password. It is never printed by the script; keep it out of
   screenshots, chat and commits.

## Step 1 — apply to the LOCAL DEVELOPMENT database only (Windows cmd)

Run from `backend\`. Replace the `SECRET_KEY` value with the same one in your `backend\.env`.

```cmd
cd /d C:\Users\garah\PycharmProjects\VANTAGE\backend

rem --- point THIS session at your local development database, and nowhere else ---
set "DATABASE_URL=postgresql+asyncpg://valora_user:valora_password@localhost:5432/valora_db"
set "SECRET_KEY=<the same long value as backend\.env>"
set DATABASE_URL
rem Expect: DATABASE_URL=postgresql+asyncpg://valora_user:valora_password@localhost:5432/valora_db

rem --- 1a. bring the schema up to head (valora_db is currently at 103dd39ca30e) ---
venv\Scripts\python.exe -m alembic -c alembic.ini heads
venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
venv\Scripts\python.exe -m alembic -c alembic.ini current
rem Expect stderr/stdout to end at: d9f2a4c7e1b3 (head)

rem --- 1b. dry run: writes nothing, prints the target and the plan ---
venv\Scripts\python.exe scripts\provision_estate.py estate --file pilot\estate.test.json --expect-database valora_db
rem Expect: "Target database: localhost:5432/valora_db", then the estate, 12 units,
rem the admin, the provider and 2 memberships, then "[dry-run] no changes were written."

rem --- 1c. write it, once you have read the plan ---
venv\Scripts\python.exe scripts\provision_estate.py estate --file pilot\estate.test.json --expect-database valora_db --apply
rem Expect: "Applied: estate #<id>, 12 units, 2 users, 1 provider profile, 2 memberships."
rem followed by the one-time passwords. COPY THEM NOW - they are shown once and stored hashed only.
```

Notes for step 1:

- **The upgrade in 1a is the one step I did not run** (it writes schema to your development
  database). `103dd39ca30e` is in the repo history, so it should be a straight walk forward; if
  Alembic reports a missing revision or a conflicting change, stop and say so rather than editing any
  migration.
- Take a `pg_dump` of `valora_db` first if anything in it matters (runbook section 5 — those
  commands were written, not run).
- The estate id is printed by the `--apply` run itself (`Applied: estate #<id>, ...`). To read it
  back later, keep this small script as `pilot\show-estates.py` and run it from `backend\`; the
  query below is the one I ran, and against `valora_db` as it stands it answered correctly by
  reporting the missing table (`UndefinedTableError: relation "estates" does not exist`) — after
  step 1a it lists the estates instead:

  ```python
  import asyncio, asyncpg

  async def go():
      conn = await asyncpg.connect(
          "postgresql://valora_user:valora_password@localhost:5432/valora_db", timeout=10
      )
      try:
          print(await conn.fetch("select estate_id, name from estates order by estate_id"))
      finally:
          await conn.close()

  asyncio.run(go())
  ```
- The script is idempotent: a second `--apply` creates nothing and reports what it skipped.
- Do **not** run `python -m app.cli seed-demo` against this database. Nothing refuses it by name
  (`valora_db` carries no demo marker), which is exactly why rule 1 of the runbook is a habit rather
  than a guard.

## Step 2 — link one resident test account to a unit (Windows cmd)

Registration is self-service and **does not attach a membership**: `POST /api/v1/auth/register`
creates a resident with no estate link, so the account sees an empty estate list until you link it.

```cmd
rem --- 2a. in the browser: register the resident at http://localhost:5173/register ---
rem          Use a .test address, e.g. amberfield.resident.one@example.test
rem          When it asks for a unit number, enter AMB-01 (or whichever unit is theirs).

rem --- 2b. dry run the link (reads only) ---
venv\Scripts\python.exe scripts\provision_estate.py link-resident --estate-id <id from step 1c> --email amberfield.resident.one@example.test --unit-no AMB-01 --expect-database valora_db
rem Expect: "resident to link: ... -> unit AMB-01", or a WARNING when the unit number the resident
rem typed at registration differs from the one you are linking. Confirm with them before applying.
rem An unknown email or a unit that is not in this estate is an ERROR with exit code 1.

rem --- 2c. write the membership ---
venv\Scripts\python.exe scripts\provision_estate.py link-resident --estate-id <id> --email amberfield.resident.one@example.test --unit-no AMB-01 --expect-database valora_db --apply
rem Expect: "Applied: 1 resident memberships created."

rem --- 2d. prove it: the resident signs in again and GET /api/v1/estates/mine lists Amberfield Valley ---
```

For several residents at once, put `email,unit_no` pairs in a CSV and use
`link-residents-csv --estate-id <id> --file pilot\residents.csv --expect-database valora_db`, dry run
first.

Caveat from the runbook that still applies: there is **no password reset**, so keep the resident's
password somewhere safe for the test, and remember an operator cannot recover it later.

## Written, not run

- `alembic upgrade head` against `valora_db` (step 1a) — it writes schema to your development
  database, which this task did not authorise.
- The `--apply` provisioning run (step 1c) and the resident link (step 2c).
- The backup/restore commands in runbook section 5.

## Findings worth knowing

1. **The provider trade value does not line up across the two features.** I used `plumbing` because
   that is what the provider directory offers and filters on
   (`frontend/src/lib/display.ts` → `trades = plumbing | electrical | security | garden | cleaning |
   building`) and what the script's own docstring example uses. The AI triage suggestion uses a
   different vocabulary — `plumber | electrician | security | landscaping | general_maintenance |
   pest_control | roofing | other` — so the triage panel's "Find plumber providers" link lands on a
   filter that matches nothing while providers are stored as `plumbing`. The script accepts any
   non-empty trade string, so neither value is rejected; the fix is to reconcile the vocabularies,
   not to pick a value here.
2. `valora_db` is far behind head and carries pre-tenancy tables. The upgrade path is plausible but
   unverified on this machine.
3. Provisioned accounts are created with `hoa_approved` and `email_verified` set to `true`, but
   **no code path checks either flag** (runbook NOT READY item 6) — it is bookkeeping, not an
   approval gate.
4. The pilot database must stay separate from the demo database, the test database
   (`TEST_DATABASE_URL` must contain `test`) and the throwaway `valora_ai5_wiring` database used for
   the AI-5 wiring check. If you ever dry run against `valora_ai5_wiring`, do not `--apply` there.

## Open questions

- Which unit the resident should actually hold, and whether their registration-time unit number will
  match the one linked (the script warns; it will not stop you).
- Whether you want the fictional admin/provider accounts registered with real credentials later, or
  replaced by real people at pilot time.
