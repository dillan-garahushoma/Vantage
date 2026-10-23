# VALORA — agent instructions

VALORA is a South African private-estate property-health platform: FastAPI modular monolith, async SQLAlchemy, PostgreSQL, Alembic. A React frontend comes later. Backend root: `backend/`. The tenant boundary is the **estate**.

Read these first, in order: `CLAUDE_README.md`, `ARCHITECTURE_AND_DOMAIN.md`, `EXECUTION_ROADMAP.md`, `DEVELOPMENT_AND_VALIDATION.md`, then every file in `docs/progress/`.

## How work is given to you
- Work arrives as **one batch per session**, as a file under `batches/` (for example `batches/phase1/phase1__batch-A.md`). Do only that batch. Do not start another, even if you have budget left.
- Follow the batch file exactly. If it conflicts with this file, the batch file wins for that batch.
- If something in the batch is already done or does not match the real code, say so and do the smallest correct thing. Do not redesign.

## Environment (Windows)
Use the repo interpreter explicitly. A bare `python` is not reliably on PATH.

```text
Tests:       backend\venv\Scripts\python.exe -m pytest backend/tests -q
Compile:     backend\venv\Scripts\python.exe -m compileall -q backend/app
Lint:        backend\venv\Scripts\python.exe -m flake8 backend/app backend/tests --count --select=E9,F63,F7,F82 --show-source --statistics
Diff check:  git diff --check
Migrations (offline SQL, run from backend\):
             venv\Scripts\python.exe -m alembic -c alembic.ini heads
             venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head --sql
```

Alembic needs `DATABASE_URL` and `SECRET_KEY` set; the values in `backend/.env.example` work.
Integration tests run only when `TEST_DATABASE_URL` is set, and only against a database whose name contains `test`. Never point it at `valora_db`. If the variable is not set in your terminal, integration tests skip. Say so in your report; do not count a skip as a pass.

## Architecture rules
- Routers: HTTP, DTOs, dependency wiring only. Services: authorization, lifecycle, business rules. Repositories: queries and persistence. SQLAlchemy models are never API DTOs.
- No business logic in React or in routers. No Living Score maths outside the backend service.
- Multi-step use cases commit **once** in the service; repositories used in them flush, not commit.
- Do not add microservices, queues, vector stores, LLM/ML code, or cloud infrastructure.
- Keep edits small and additive. Do not rewrite stable or legacy modules for style.

## Security rules (non-negotiable)
- Every estate-scoped read/write goes through `EstateAuthorizationService.resolve_access`, then an estate-scoped repository method. A client-supplied `estate_id` is never proof of access.
- Not a member of the estate: 403. Object belongs to another estate: 404.
- HOA and provider capability needs both the global role and a matching estate membership.
- Public registration creates residents only.
- Never read, print, or log `.env`, passwords, tokens, or invitation codes.

## Working rules
- Write the failing test first, then the fix.

- **Honesty rule:** never claim something ran unless you ran it and saw the output. Label the rest "written, not run".
- At the end of the session, or at about 70% of your budget, write `docs/progress/<phase>-<batch>.md`: done, tests added and passing, written-but-not-run, remaining, deviations, open questions, and the exact commands you ran with results. Then stop.
- If you stall or loop, stop and say so. Do not retry the same approach repeatedly.

## Skills
Skills are plain files. Open the relevant ones directly from `.agents/skills/`:
`valora-session-protocol`, `valora-testing`, `valora-security-review`, `valora-migration-safety`, `valora-code-review`, `valora-architecture`, `valora-api-contracts`, `valora-domain-model`, `valora-data-strategy`, `valora-living-score`, `valora-product-design`, `valora-quality-gates`.
For backend batches, at minimum read `valora-session-protocol`, `valora-testing`, and the skill that matches the work (migrations: `valora-migration-safety`; authorization or invitations: `valora-security-review`).

Third-party frontend and design skills are installed alongside them: `design-taste-frontend` (Taste Skill v2 art direction), `image-to-code`, `web-design-guidelines` (Vercel Web Interface Guidelines review), `awesome-design-md` (real-world `DESIGN.md` design systems), and `playwright-cli` (browser automation through the installed `@playwright/cli`). Read the matching one before building or restyling any user-facing React surface, and read `frontend/DESIGN.md` first — it is the frontend's visual contract (registers, tokens, section blueprints, the Group8 adaptation map). They inform design decisions only; the architecture and security rules in this file still decide behaviour.

On this Windows machine Chrome is not installed and Edge quits immediately in headless mode, so the Taste Skill inspector needs the Playwright-bundled Chromium: set `CHROME_PATH=%LOCALAPPDATA%\ms-playwright\chromium-1247\chrome-win64\chrome.exe` before `node .agents/skills/design-taste-frontend/scripts/inspect.mjs ...`. `playwright-cli` is configured for the same browser by `.playwright/cli.config.json` and needs no extra flags.
