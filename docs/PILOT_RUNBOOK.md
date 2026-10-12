# PILOT RUNBOOK — a real estate, real people, no seed data

BATCH PILOT-1. This runbook is for the operator who stands up the first **real**
pilot estate and measures whether the AI assist layer is worth keeping.

It is written against the code as it exists today. Where the code cannot yet do
something, that is listed under [NOT READY](#not-ready-verified-against-the-code)
rather than glossed over.

Read this with:

- `docs/ADR-004-AI-Assist-Layer.md` — why the AI layer is built the way it is
  (off by default, never load-bearing, ledger of metadata only);
- `docs/ADR-001-Estate-Tenancy.md` and `docs/ADR-002-estate-authorization.md` —
  the estate is the tenant boundary, so a pilot is one estate;
- `docs/ADR-005-Living-Score-Authority.md` — which score is authoritative. The
  five-component estate-level `v1.0.0` score is Living Score; the legacy
  40/30/30 per-property route is not, and is not yet replaced.
- `docs/progress/ai-1.md`, `docs/progress/ai-2.md`, `docs/progress/ai-3.md` —
  what is actually implemented in each AI batch.

---

## 1. Demo and pilot are two different worlds

| | Demo | Pilot |
| --- | --- | --- |
| Purpose | Local development, screenshots, training | A real estate with real residents |
| Database | anything named `*demo*` (`valora_demo`), named on the command line | Its own database, e.g. `valora_pilot` |
| Data | `python -m app.cli seed-demo --expect-database valora_demo` (`app/seed_demo.py`) creates the demo estate with `estates.is_demo = true` | `scripts/provision_estate.py` creates a real estate with `estates.is_demo = false` |
| AI flags | Off, or `fake` provider | On, per section 4, once POPIA says so |

Rules that keep the two apart:

1. **Never run the demo seeder against the pilot database**, and never run the
   provisioning script against the demo database. The seeder refuses any database
   whose name does not contain `demo` **and** refuses any database other than the
   one passed to `--expect-database`, both checked against the live connection;
   `provision_estate.py` refuses to write into a database whose name looks like a
   demo database unless you pass `--allow-demo-database`; and no migration flips
   `is_demo`.
2. **Give the pilot its own `DATABASE_URL`**, in its own shell profile or secret
   store — not a shared `.env` that a demo command might pick up.
3. `scripts/provision_estate.py` and `scripts/ai_pilot_report.py` **read
   `DATABASE_URL` from the environment only, never from `.env`**. That is
   deliberate: the host and database name they print at the start of every run
   are provably the database they will touch.
4. Use `--expect-database valora_pilot` on every write. It refuses the run when
   the target name is not what you typed, which is the cheapest guard against
   the one mistake that cannot be undone.

The pilot database is separate from the demo database *and* from the test
database. `TEST_DATABASE_URL` must always contain `test`; never point it at the
pilot.

---

## 2. Environment and secret handling

Names must match `backend/app/core/config.py` exactly. `backend/.env.example`
is the template; it holds placeholders only.

| Variable | Why it matters for a pilot |
| --- | --- |
| `DATABASE_URL` | The pilot database. Full SQLAlchemy async URL. Contains the password — never print it, never commit it. |
| `ENVIRONMENT` | Anything other than `development` tightens `SECRET_KEY` validation (length ≥ 32, no known placeholder). Set it to a non-development value for the pilot. |
| `SECRET_KEY` | Signs the access tokens residents hold. Generate a long random value and keep it in the secret store, not in git. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 by default. |
| `CORS_ORIGINS` | A JSON array of explicit origins. `*` is rejected at startup. Put the real pilot origin here. |
| `LOGIN_MAX_FAILED_ATTEMPTS`, `LOGIN_LOCKOUT_WINDOW_MINUTES` | Login throttling; 5 failures in 15 minutes by default. |
| `AI_*` | See section 4. All off by default. |
| `GEMINI_API_KEY` / `AI_COMPAT_API_KEY` | Provider credentials. Put them in the environment or the host's secret store. **Never** in git, in a chat message, or in this repository's files. |

Secrets come from the runtime environment. Nothing in the codebase reads a key
from a file in the repo, and the AI layer never logs a key, a prompt or a
provider response — the ledger tables (`ai_call_events`,
`complaint_ai_suggestions`) store scalar labels and counts only, which is what
makes them safe to report on.

Passwords for provisioned accounts are a separate case: `provision_estate.py`
generates them with `secrets`, prints them **once** to stdout under `--apply`,
and stores only the hash. If you lose one, re-provision a new account — there is
no recovery path yet (see NOT READY).

---

## 3. Stand up the pilot estate

Run from `backend/`. Use the repo interpreter; a bare `python` is not reliably on
PATH on Windows.

```bash
# 1. Point at the pilot database in THIS shell (not .env)
export DATABASE_URL="postgresql+asyncpg://USER:PASSWORD@HOST:5432/valora_pilot"
export SECRET_KEY="<a long random value>"
export ENVIRONMENT="pilot"     # anything that is not "development"

# 2. Migrate the pilot database, then prove the head matches
venv/Scripts/python.exe -m alembic -c alembic.ini upgrade head
venv/Scripts/python.exe -m alembic -c alembic.ini heads

# 3. Prepare the estate file (units, HOA admins, providers)
#    See the estate file format in scripts/provision_estate.py's docstring.
vim pilot-estate.json

# 4. DRY RUN FIRST - writes nothing, prints the target database and the plan
venv/Scripts/python.exe scripts/provision_estate.py estate \
    --file pilot-estate.json --expect-database valora_pilot

# 5. Read the plan, then write
venv/Scripts/python.exe scripts/provision_estate.py estate \
    --file pilot-estate.json --expect-database valora_pilot --apply
```

The dry run prints the target database host and name (password redacted), the
estate, every unit, every account and every membership it would create, plus
anything it will skip because it already exists. Nothing is written without
`--apply`.

**Store the generated passwords now.** They are printed once and never again.

The script is idempotent: run it a second time and it creates nothing, reports
what it skipped, and exits 0. It sets `estates.is_demo = false`, and it refuses
to reuse a unit number that already exists in any other estate (the schema only
requires uniqueness per estate, but a pilot should never have two units sharing
a number).

### Then onboard residents

Residents register themselves through the public API
(`POST /api/v1/auth/register`, residents only), and registration does **not**
attach them to a unit. Linking is a separate, operator-driven step:

```bash
# One resident
venv/Scripts/python.exe scripts/provision_estate.py link-resident \
    --estate-id 1 --email resident@example.com --unit-no PL-01 \
    --expect-database valora_pilot --apply

# A batch, from a CSV with the columns email,unit_no
venv/Scripts/python.exe scripts/provision_estate.py link-residents-csv \
    --estate-id 1 --file residents.csv \
    --expect-database valora_pilot --apply
```

Each link creates an estate membership whose role is `resident`, with
`property_id` set to the unit. The dry run (omit `--apply`) prints exactly what
would be created, plus:

- a **warning** when the resident's self-declared `unit_no` differs from the one
  you are linking them to — confirm with the resident before applying;
- a **warning** when they are already linked to a different unit in this estate
  (they will then hold both);
- an **error**, with exit code 1 and nothing written for that row, when the email
  has no registered account or the unit does not exist in this estate.

Resident onboarding checklist:

1. Share the app URL and the fact that registration is self-service.
2. Resident registers with their real email and unit number.
3. Operator links them with `link-resident` (dry run, then `--apply`).
4. Resident logs in and can see the estate in `GET /api/v1/estates/mine`.
5. Confirm the "estate visible" step actually happened — a resident whose
   membership is missing sees an empty list, not an error.

---

## 4. Turning the AI layer on (order matters)

The AI layer is **off by default and the product works with it off**. Enabling a
flag is a product decision, not a technical one, so follow this order:

1. **`AI_INSIGHTS_ENABLED=true` first** (with `AI_ENABLED=true` and a provider
   configured). This is the read-only assist on aggregate estate health: the
   Estate Health Brief sends the provider **aggregates only** — the numbers of the
   latest stored Living Score snapshot — never a resident's name, unit number,
   complaint text or any other personal data. Measure it before anything that
   touches resident-written text.
2. **`AI_TRIAGE_ENABLED=true` and `AI_PERSONAL_DATA_ALLOWED=true` only after**
   the provider-terms and POPIA checklist in section 7 is signed off. Triage
   reads complaint text, which is personal data written by a resident, so it
   needs the explicit opt-in that `AI_PERSONAL_DATA_ALLOWED` provides.

Full set for a pilot with AI on:

```bash
export AI_ENABLED=true
export AI_PROVIDER=gemini            # or openai_compatible
export AI_MODEL="<model name>"
export GEMINI_API_KEY="<from the secret store>"
export AI_INSIGHTS_ENABLED=true      # step 1
# export AI_TRIAGE_ENABLED=true      # step 2, after sign-off
# export AI_PERSONAL_DATA_ALLOWED=true  # step 2, after sign-off
export AI_DAILY_CALL_CAP_PER_ESTATE=200   # per-estate daily budget
```

Notes verified in `app/core/config.py` and `app/core/ai/`:

- `AI_ENABLED` is the master switch; `AI_PERSONAL_DATA_ALLOWED=true` is refused
  at startup unless `AI_ENABLED=true`.
- `AI_PROVIDER=fake` is refused outside `development` and `test`. Do not try to
  pilot on the fake provider.
- Feature names are `insights` and `triage`; each maps to its own flag
  (`app/core/ai/client.py`). A feature with no flag never reaches a provider.
- The per-estate daily cap (`AI_DAILY_CALL_CAP_PER_ESTATE`) is enforced against
  the append-only `ai_call_events` ledger. Over-budget calls are recorded as
  `rejected_budget`, not silently dropped — which is what makes the report's
  rejection counts meaningful.
- Every call is recorded in `ai_call_events` with its feature, status, reason and
  latency. Never a prompt, never a response.

### Kill switch

```bash
export AI_ENABLED=false   # master switch off
# restart the API process
```

Settings are read through a cached settings object built at import time, so a
restart is what actually applies the change — editing the environment of a
running process does nothing. After the restart:

- AI calls raise `AIUnavailableError` and the features degrade to "no
  suggestion"; a complaint is unaffected either way, because nothing in the
  product depends on a suggestion existing.
- Confirm the kill switch took effect: `scripts/ai_pilot_report.py` should show
  no new `ai_call_events` rows for the window, and normal complaint submission
  must still work end to end.

The kill switch is `AI_ENABLED`, not the provider key. Deleting the key without
setting the flag leaves the feature enabled and failing, which is noisier than
turning it off.

### Measuring the pilot

```bash
venv/Scripts/python.exe scripts/ai_pilot_report.py --estate-id 1 --days 30
```

Read-only (`SELECT` only). It reports:

- AI calls by feature, status and reason, with average and p95 latency for the
  calls that were actually timed;
- triage decisions — accepted, overridden, dismissed — as counts and rates, with
  `n` shown and an explicit note that a sample below 30 is not meaningful;
- a Health Brief section that says "not available yet" until those tables are
  wired into this script (AI-4 creates them as `ai_insights` /
  `ai_insight_feedback`; the script's `BRIEF_TABLES` probe still looks for
  `health_briefs` / `health_brief_feedback`, so it reports them as absent).

Run it weekly for the pilot's length and keep the output. A rate on its own is
not evidence; the decision to keep or drop the AI layer should rest on the
accepted/overridden split and on whether the HOA admins actually wanted the
suggestions.

---

## 5. Backups (documented, **not run**)

**These commands were written, not run.** Adapt them to the host and test the
restore into a scratch database before the pilot starts. A backup you have never
restored is not a backup.

```bash
# Dump the pilot database (custom format, so it can be restored selectively).
# Prompt for the password rather than putting it on a command line.
pg_dump --format=custom --no-owner --file=valora_pilot_$(date +%Y%m%d).dump \
        --dbname=postgresql://USER@HOST:5432/valora_pilot

# Verify the dump is readable before trusting it.
pg_restore --list valora_pilot_20261010.dump | head

# Restore into a SCRATCH database (never over the live pilot) and check it.
createdb -h HOST -U USER valora_restore_check
pg_restore --no-owner --dbname=postgresql://USER@HOST:5432/valora_restore_check \
        valora_pilot_20261010.dump
psql -h HOST -U USER -d valora_restore_check -c '\dt'
psql -h HOST -U USER -d valora_restore_check \
     -c 'select count(*) from estates; select count(*) from users;'
```

Take a dump before every migration and before every `--apply` run. The AI ledger
is append-only and small; include it — it is the measurement.

---

## 6. What to watch during the pilot

- `GET /health` — liveness only. It says nothing about the database or the AI
  provider (see NOT READY).
- `scripts/ai_pilot_report.py` — weekly, as above.
- Application logs — request ids, status codes, and error codes. If you see a
  prompt, a response or a resident's words in a log line, that is a bug: the AI
  layer is built so it cannot happen, and it should be reported immediately.

---

## 7. POPIA checklist

**This is a checklist to take to a lawyer. It is not legal advice**, and passing
it is not a claim of compliance. Work through it before enabling
`AI_TRIAGE_ENABLED` or `AI_PERSONAL_DATA_ALLOWED`, because triage sends
resident-written text — personal data, and untrusted input — to a provider.

- [ ] **Privacy notice** in place and shown at registration: what is collected,
      why, for how long, who it goes to (including an AI provider), and how to
      complain to the Information Regulator.
- [ ] **Lawful basis / consent** recorded for processing resident-written
      complaints, and a separate, explicit basis for sending that text to an AI
      provider. Note that consent is not the only possible basis; decide with
      counsel.
- [ ] **Operator agreement** (POPIA section 20/21 terms) signed with the AI
      provider, covering purpose limitation, confidentiality and security.
- [ ] **Cross-border transfer** assessed and documented: if the provider
      processes outside South Africa, the section 72 conditions apply.
- [ ] **Retention**: how long complaints, the AI ledger and any generated text
      are kept, and how they are destroyed. The ledger is metadata-only, which
      helps, but it is still estate history.
- [ ] **Data-subject requests**: a route for access, correction and deletion,
      with a stated turnaround, and a decision on what happens to an AI
      suggestion attached to a deleted complaint.
- [ ] **Information officer** registered and contactable; the residents know who
      that is.
- [ ] **Security safeguards**: encryption in transit, restricted database
      access, key handling per section 2, and no resident text in logs.

Related: anonymity is only partial. An anonymous complaint still carries
`unit_id`, which can identify the author (documented residual in the security
review skill). Do not promise residents more anonymity than the system provides.

---

## NOT READY (verified against the code)

These were checked in the real tree, not assumed. Each one blocks a *comfortable*
pilot, though not necessarily the first pilot:

1. **Password reset is operator-only.** There is no forgot-password endpoint, no
   reset token and no email sending. The interim is
   `scripts/reset_password.py --email … --expect-database … --apply`, which prints
   a new password **once** (dry run by default, never logged, bcrypt hash only).
   That is a phone call to the operator, not self-service: design the workaround
   with the pilot estate before onboarding, or accept that support is manual.
2. **Membership has two doors and no approval flow.** A resident self-registers
   and redeems an estate join code against a unit; an HOA administrator adds a
   *provider* by email. There is still no invitation module and no
   approve-a-member endpoint, so a member is never re-checked by a human. The
   join code is the proof of the right to join — whoever holds a live code can
   join — so rotate it when it has been shared too widely.
3. **Hosting and TLS are not ready.** `docker-compose.yml` is a local demo and
   development stack: `uvicorn --reload` on port 8000 (a development server), no
   TLS termination, no reverse proxy, no process manager, uploads on the host's
   local disk, and migrations applied automatically on container start. The only
   rate limiting is per-account login and join attempts, in-process. The pilot
   needs a host that terminates TLS (with the real origin in `CORS_ORIGINS`, or
   residents are sending passwords in the clear), a process manager, and a
   decision about where photographs live. See
   [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) for the full list.
4. **Monitoring is a single liveness endpoint.** `GET /health` only. There are no
   metrics, no error tracking, no alerting, and no dashboard. During the pilot,
   failures are found by someone noticing them — so the weekly report and a
   manual look at the logs are the monitoring.
5. **Email is not sent by anything.** No email transport exists in the code, so
   there is no invite email, no password reset email and no notification email.
6. **`hoa_approved` and `email_verified` gate nothing.** They are returned in the
   user DTO but no code path checks them. Provisioned accounts are created with
   both set to `true`; that changes no authorisation decision today, and it must
   not be treated as an approval workflow.
