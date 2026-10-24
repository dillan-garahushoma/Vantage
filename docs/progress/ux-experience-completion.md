# VALORA — UX Experience Completion Report

**Session Date:** 2026-10-23  
**Branch:** `codex/valora-experience-completion`  
**Assigned Batch:** `batches/ux-experience-completion.md`  
**Authority:** `docs/CODEX_UX_REDESIGN_BRIEF.md` and `AGENTS.md`  

---

## 1. Executive Summary

We executed `batches/ux-experience-completion.md` as the single assigned implementation batch on branch `codex/valora-experience-completion`. The work unified the disconnected Ask VALORA functionality into the VALORA Intelligence page, eliminated the redundant global sidebar Living Score widget, fixed server-side public directory filtering by province, and refined the resident, HOA, and provider role journeys within the established light-purple VALORA visual identity.

---

## 2. Implemented Changes

### A. Ask VALORA & VALORA Intelligence Unification
- **Single Intentional Entry Point:** Removed the global top-bar Ask VALORA spotlight launcher button from `frontend/src/components/layout/TopBar.jsx` and detached `AskValoraSpotlight` from `frontend/src/components/AppShell.jsx`. Ask VALORA is now anchored in its dedicated workspace: VALORA Intelligence (`/intelligence` and `/app/intelligence`).
- **Real SSE Streaming Integration:** Rewrote `frontend/src/components/valora/AskValora.jsx` to stream real tokens via `streamAskValora` from `frontend/src/lib/intelligence.js` (`POST /api/v1/analytics/intelligence/ask/stream`), supporting multi-turn conversation history.
- **Role-Aware Context & Grounding:**
  - Automatically adapts suggestions from `rolePrompts[role]` (`hoa_admin`, `resident`, `service_provider`).
  - For HOA admins: `"What is the operational risk summary for this week?"`, `"Which work orders are currently overdue?"`, `"Summarise open complaints and contractor performance."`
  - For residents: quiet hours, maintenance request status, Living Score meaning.
  - For providers: assigned jobs, gate access hours, SLA deadlines.
- **Structured Output Presentation (`AiAnswerRenderer`):**
  - Model outputs render with semantic typography (headings, tables, lists, code, citation badges, action cards) with zero raw markdown markers (`**bold**`, `#`, or asterisks).
  - Contextual follow-up chips (`ROLE_FOLLOW_UPS[role]`) allow continuous dialogue with one click.
  - Native copy-to-clipboard button with visual feedback.
  - Reset / "New session" control to start a fresh conversation.
  - Clear privacy guarantee: reads operational records only, never private resident data.
- **Resilient Page Architecture:** Decoupled Ask VALORA and the resident/provider queues from briefing generation errors so that an unavailable briefing does not blank out or disable the chat workspace.
- **Keyboard & Modal Focus:** Added expandable focus modal (`role="dialog" aria-label="Ask VALORA Intelligence"`) with backdrop blur and Escape / close handlers, whilst supporting inline conversation.

### B. Removed Duplicate Sidebar Living Score
- **Sidebar De-cluttering (`frontend/src/components/layout/Sidebar.jsx`):** Removed `LivingScoreWidget` and associated imports (`Sparkline`, `useEstate`). The Living Score is no longer repeated in the left rail on every single screen.
- **Dedicated Health Authority:** Detailed Living Score analysis, rolling 90-day trajectory, and individual component pillars remain authoritatively hosted in Estate Health (`/app/health`), with compact, decision-relevant summaries on role dashboards.

### C. Correct Estate Data Flow & Public Directory Search
- **Server-Side Province Search (`backend/app/property/repositories/estate_repository.py`):**
  - Updated `EstateRepository.public_statement` to include `Estate.province.ilike(pattern)` alongside name, suburb, and city.
  - Updated `backend/app/property/api/public.py` query documentation to reflect province search.
  - Fixes regional filtering so clicking province filter pills (`Western Cape`, `Gauteng`, `KwaZulu-Natal`) queries the entire database server-side instead of filtering only the first page in memory.
- **Landing Page Catalogue (`frontend/src/routes/Landing.jsx`):**
  - Wired `FeaturedEstates` to pass `q: selectedRegion` directly to `listPublicEstates`.
  - Updated "Explore full directory" link to preserve the selected region in URL search parameters (`/estates?q=...`).
- **Data Integrity & Musgrave Tracing:**
  - Traced public directory SQL queries: strictly filtered by `Estate.is_public.is_(True)` and `Estate.is_demo.is_(False)`.
  - No client-side exclusion hack (e.g. `!name.includes("Musgrave")`) was introduced.
  - Production database verification requirement documented below.

### D. Resident, HOA & Service Provider Workspaces
- **Resident Workspace (`Dashboard.resident.jsx`):** Clear estate context and linked unit counts, prominent maintenance issue reporting CTA, "Your active requests" queue with status chips and relative timestamps, official announcements, and compact Living Score indicator.
- **HOA Administrator Workspace (`Dashboard.admin.jsx`):** Leads with triage banner for unassigned complaints requiring contractor dispatch, operational KPI row (complaints, resolution rate %, average resolution hours, work orders in flight), compact Living Score snapshot, and needs-attention queue.
- **Service Provider Workspace (`ProviderWork.jsx` & routing):** Automatic routing from `DashboardRouter` to `/provider/work` (`My work`), preventing access to resident or HOA dashboards.
- **Router Navigation (`App.jsx`):** Added redirect route `/app/intelligence` -> `/intelligence`.

---

## 3. Automated Validation Results

All checks were executed locally against the codebase:

| Check / Command | Result | Details |
|---|---|---|
| `backend\venv\Scripts\python.exe -m compileall -q backend/app` | **Pass (0 errors)** | Backend Python compiles cleanly |
| `backend\venv\Scripts\python.exe -m flake8 backend/app backend/tests --count --select=E9,F63,F7,F82 --show-source --statistics` | **Pass (0 errors)** | Python lint passed with 0 violations |
| `git diff --check` | **Pass (0 errors)** | No whitespace or merge marker issues |
| `cmd /c "cd frontend && npx vitest run src/routes/Intelligence.test.jsx src/components/valora/AiAnswerRenderer.test.jsx src/components/valora/AskValoraSpotlight.test.jsx src/App.routes.test.jsx"` | **Pass (17/17 tests passed)** | 8 tests in `Intelligence.test.jsx`, 4 in `AiAnswerRenderer.test.jsx`, 3 in `AskValoraSpotlight.test.jsx`, 2 in `App.routes.test.jsx` |
| `npm.cmd --prefix frontend run build` | **Pass (0 errors)** | Vite production bundle built successfully in 1m 4s (`dist/assets/index-Ws4J8mWg.js`) |
| `backend\venv\Scripts\python.exe -m pytest backend/tests/test_onb_master_p2_photos_and_public.py -q` | **Pass (16 passed, 8 skipped)** | Public directory API tests passed (8 skipped due to absence of live test database URL) |

---

## 4. Tests Written, Not Run & External Verification

- **Full Playwright E2E Suite:** Not run to conserve session token and execution budget per batch instructions.
- **Production Database Read-Only Query (Musgrave):**
  - If an unwanted record (e.g. seeded during development) appears in a live deployment, run the following read-only query to inspect the database row before any modification:
    ```sql
    SELECT estate_id, name, suburb, city, province, is_public, is_demo, created_at
    FROM estates
    WHERE suburb ILIKE '%Musgrave%' OR name ILIKE '%Musgrave%';
    ```
  - If the estate is a test or seed fixture, ensure its flags are set to `is_demo = true` and `is_public = false`, rather than deleting operational history.
- **Live AI Provider Credentials:** The local test suite validated SSE streaming with mocked generator fixtures. External verification against the live Gemini / LLM provider requires production API credentials (`GEMINI_API_KEY` or configured gateway).

---

## 5. Files Changed

1. `backend/app/property/repositories/estate_repository.py` — added province matching to `public_statement`
2. `backend/app/property/api/public.py` — updated query parameter documentation for province support
3. `frontend/src/components/layout/Sidebar.jsx` — removed duplicate `LivingScoreWidget`
4. `frontend/src/components/layout/TopBar.jsx` — removed global Ask VALORA spotlight launcher
5. `frontend/src/components/AppShell.jsx` — removed global `AskValoraSpotlight` modal mount and unused chat context
6. `frontend/src/components/valora/AskValora.jsx` — full streaming LLM client, role suggestions, history, `AiAnswerRenderer`, copy, reset, and modal focus
7. `frontend/src/components/valora/AskValoraSpotlight.jsx` — updated aria-label to match test contract
8. `frontend/src/routes/Landing.jsx` — server-side province filtering for published catalogue
9. `frontend/src/App.jsx` — added `/app/intelligence` alias route to `/intelligence`
10. `docs/progress/ux-experience-completion.md` — this completion report


---

## 6. Follow-up implementation — portal composition and account switching

**Follow-up session:** 2026-10-23  
**Scope:** The supplied current-state screenshots and dashboard concept.

### Changes in this follow-up

- `frontend/src/routes/Register.jsx`: Added three visible role paths (Resident, HOA / estate manager, Service provider). Public self-registration remains resident-only; selecting a trusted role displays the real provisioning path and never submits a privileged role.
- `frontend/src/routes/Login.jsx`: Added a current-session choice to continue or explicitly sign out and use another account. This avoids silent redirects that can trap the user outside the sign-in form.
- `frontend/src/routes/Register.test.jsx`: Added coverage for the role options, provisioning notices, and resident-only registration payload. The accessible-name selector was corrected after CI showed that the role descriptions are included in a radio's computed accessible name.
- `frontend/src/routes/Dashboard.resident.jsx`: Rebuilt the resident overview with the existing estate photo asset, personalised greeting, open-request list, notices, and compact Estate Health summary. Uses actual estate-scoped API responses; a missing score is shown as insufficient data, not zero.
- `frontend/src/routes/Dashboard.admin.jsx`: Rebuilt the HOA overview around estate context, priority issues, a restrained operational metric strip, work orders, notices and recent activity. Complaint details use the existing Radix drawer primitive for focus trapping and Escape/dismiss behaviour. The open-complaint metric uses backend aggregate status counts instead of treating the latest loaded page as the entire estate.
- `frontend/src/routes/Dashboard.livingScore.test.jsx`: Updated assertions for the new compact score summary and action label.
- `.github/workflows/ci.yml`: Added a frontend job that runs `npm ci`, `npm run build`, and `npx vitest run` on PRs.

### Validation for the dashboard/account follow-up

- GitHub Actions run **40026245541** (head `ef6aa1fc05251b5c347ff3a5ad63a3287f731fd2`):
  - Frontend production build: **passed**.
  - Frontend Vitest suite: **passed**.
  - At the time this addendum was written, the backend job was still running; no backend-suite conclusion is claimed.
- The local container could not resolve `github.com`, so no local `npm` command was run. The CI result above is from GitHub Actions.
- No authenticated live-browser screenshot review, live backend/API session, production AI check, or production database mutation was performed.
- The existing `/estate-hero.jpg` is being reused as a temporary architectural asset and can be replaced later.

### Delivery state

The changes are pushed to `codex/valora-experience-completion` and available in draft pull request #2. They are **not merged to `main` and not deployed**. Browser/production acceptance is still required before a release.

## 7. Follow-up — restore the owner-confirmed published estates

**Follow-up session:** 2026-10-24
**Owner clarification:** The five previously listed estates are genuine properties, not demo estates.

### Diagnosis and changes

- Rechecked the deployed public API: it still returns one listing (`musgrave`, estate ID 7; `total: 1`); public detail for IDs 4, 5, 6 and 8 returns 404. The prior code fix was not deployed and did not restore or repair the estate records.
- Commit `12bf2f8` added `is_demo = false` as an additional visibility gate; migration `e2f4c8b1a9d3` then marked the five known estates demo/private. Both changes hid the owner-confirmed estates.
- Public directory list and detail now use explicit publication (`is_public`) as the visibility gate.
- Added migration `f3a6b2c9d1e4` to restore only the five exact known estate names as non-demo and public, retaining their historical score-publication setting when available. It also unpublishes only the verified Musgrave identity (exact name and location); it does not delete the record or its history. The migration archives current flags to support downgrade.
- Added migration regression tests for the five estate identities, the publication flags, the narrowly matched Musgrave row, and restoring flags on downgrade. Updated the deployment guide to document the publication rule.

### Validation and remaining

- `C:\Users\garah\AppData\Local\Programs\Python\Python312\python.exe -m pytest backend\tests\test_restore_published_estates_migration.py backend\tests\test_seed_demo_migration.py backend\tests\test_onb_master_p2_photos_and_public.py -q` — **21 passed, 8 skipped**; the skipped tests require the configured test database.
- `C:\Users\garah\AppData\Local\Programs\Python\Python312\python.exe -m compileall -q backend\app` — **passed**.
- `C:\Users\garah\AppData\Local\Programs\Python\Python312\python.exe -m flake8 backend\app\property\repositories\estate_repository.py backend\app\property\services\public_directory_service.py backend\alembic\versions\f3a6b2c9d1e4_restore_owner_confirmed_estates.py backend\tests\test_restore_published_estates_migration.py backend\tests\test_onb_master_p2_photos_and_public.py --count --select=E9,F63,F7,F82 --show-source --statistics` — **passed, 0 selected violations**.
- From `backend\` with throwaway offline validation settings, `python -m alembic -c alembic.ini heads` — **f3a6b2c9d1e4 (head)**; `python -m alembic -c alembic.ini upgrade head --sql` — **passed**. No database connection was made.
- `git diff --check` — **passed**.
- The repository `backend\venv\Scripts\python.exe` and dedicated migration-safety skill were absent; validation used installed Python 3.12 and source-level migration tests.
- The live migration, production deployment, and browser verification remain unrun. Once deployed, verify `/api/v1/public/estates?page=1&page_size=12` lists the five intended estates, excludes Musgrave, and that the five details open successfully.

## 8. Follow-up — estate photo mosaic and landing hero

**Follow-up session:** 2026-10-24
**Scope:** Match the public estate photo collage to the supplied property-gallery reference and make the landing image a full-bleed background behind the hero content.

### Changes

- `frontend/src/components/PhotoGallery.jsx`: Rebalanced the three- and four-photo desktop layouts around a large lead image and supporting tiles, and reserved consistent 320px/380px desktop collage heights. The existing photo count, overflow, viewer, and mobile behavior remain intact.
- `frontend/src/components/PhotoGallery.test.jsx`: Added checks for the lead/supporting tile geometry and reserved desktop height.
- `frontend/src/routes/Landing.jsx`: Changed the bounded split hero into a full-width architectural image with a legibility scrim behind the copy, search, directory and sign-in actions. Shortened the heading so it fits in two lines or fewer at mobile widths, and shortened the search placeholder.

### Validation

- From `frontend\`, `.\node_modules\.bin\vitest.cmd run src/components/PhotoGallery.test.jsx` — **passed, 10 tests**.
- From `frontend\`, `npm.cmd run build` — **passed**. Vite emitted its existing advisory that the main JavaScript chunk exceeds 500 kB.
- `git diff --check` — **passed**.
- The design-taste inspector ran at 1440px, 768px and 390px and screenshots were reviewed at each listed viewport. The hero headline measured one line on desktop and tablet, two lines on mobile. The full page still reports **17 FAIL / 7 WARN**, including unrelated existing page patterns and another mobile headline; the full-page gate is not considered passed by this focused hero/gallery change.

### Remaining

- Changes are uncommitted and not pushed.
- The full-page inspector findings remain outside this follow-up's scoped hero/gallery change.
- Production deployment and live estate/API verification are still separate and unverified.
