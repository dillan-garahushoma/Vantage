# Running Phase 1 with Freebuff

Freebuff is the free, ad-supported version of Codebuff. I could not verify its model, usage limits, or availability in your country, so check those before relying on it. Treat each batch as one short session.

## One-time setup

1. Put these in the repository root: `AGENTS.md`, `knowledge.md`. Put the `batches/` folder next to them.
2. Install Node.js if you do not have it, then: `npm install -g freebuff`
3. Make sure Postgres is up and the test database exists (you already did this):
   `docker compose up -d db` from `backend\`, and `valora_test` exists.
4. Confirm Phase 0 is committed: `git status --short` should show no Phase 0 files left uncommitted.

## Before every session

In Command Prompt, from the repo root. Set the variable **in the same window you start Freebuff from**, so its terminal inherits it:

```bat
set "TEST_DATABASE_URL=postgresql+asyncpg://valora_user:valora_password@localhost:5432/valora_test"
git status --short
git add -A
git commit -m "checkpoint before phase1 <batch>"
freebuff
```

The checkpoint commit gives you a rollback point, because Freebuff may run terminal commands on its own. If `git status` shows files you do not want committed (`Guide`, `scratch/`, `docs/VALORA_PRD.md` were unexplained earlier), add only the paths you want instead of `git add -A`.

## The message to send, per batch

Start a **new** Freebuff session for each batch and send exactly this, changing only the file name:

```text
Read AGENTS.md first. Then do the task in @batches/phase1/phase1__batch-A.md.
Do only that batch. When finished, write the progress note and stop.
```

If `@file` does not load the file, paste the file's contents instead.

## Order

| Session | File | Notes |
|---|---|---|
| 1 | `phase1__batch-A.md` | Pagination envelope, sorting, OpenAPI export. Wide but mechanical |
| 2 | `phase1__batch-B.md` | Announcements and its migration |
| 3 | `phase1__batch-C.md` | Foundation schema, categories, SLA, location |
| 4 | `phase1__batch-D.md` | Security incidents |
| 5 | `phase1__batch-E1.md` | `/estates` and `/auth/me` |
| 6 | `phase1__batch-E2.md` | Invitations. Security-critical: get a second opinion |
| 7 | `phase1__batch-E3.md` | Provider provisioning. Security-critical: get a second opinion |
| 8 | `phase1__batch-E4.md` | Operator CLI |
| 9 | `phase1__batch-F.md` | Docs and ADRs |

## After every session

```bat
backend\venv\Scripts\python.exe -m pytest backend/tests -q
git diff --stat
```

- You want **0 failed** and, with `TEST_DATABASE_URL` set, **0 skipped**. If something skipped, run it again with `-rs` to see why.
- Read `docs/progress/phase1-<batch>.md`. If it says anything is "written, not run", run that yourself.
- Then commit: `git add -A` and `git commit -m "phase1 batch <X> (unreviewed)"`.
- Paste the progress note and the test output into the review chat before starting the next batch if the batch was E2 or E3.

## If a session stalls

Stop it. Start a new session with the same message. The agent reads `docs/progress/` and the real code, so it continues from the saved state. Do not keep prompting inside a stuck session.

## Privacy

Freebuff sends your code to its servers to work. The repo has no real secrets (only the dev database password and the dev key), but do not let it open `.env`, and read the vendor's data terms before using it on anything sensitive.
