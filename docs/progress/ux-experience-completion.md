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

## 7. Follow-up — restore explicitly published estates

**Follow-up session:** 2026-10-24
**Owner clarification:** The first five previously listed estates are genuine properties, not demo estates.

### Diagnosis and changes

- Read the deployed public directory endpoint. It returned one item (`musgrave`, estate ID 7; `total: 1`), matching the supplied screenshots. The frontend is rendering the backend response; there is no hardcoded Musgrave entry.
- Commit `12bf2f8` added `is_demo = false` as a second public-visibility gate in the repository and detail service. That condition hid estates explicitly published with `is_public = true`. Publication is now controlled by `is_public`; `is_demo` remains the score-data-origin flag. Seeded demo fixtures remain private because their seeder sets `is_public = false`.
- Added regression coverage proving explicitly published demo-classified estates can appear in the public list/detail, while unpublished demo estates remain hidden.
- Updated the deployment guide to document the explicit publication rule and the need to verify the configured database/record flags. No production database rows were changed.

### Validation and remaining

- `C:\Users\garah\AppData\Local\Programs\Python\Python312\python.exe -m pytest backend\tests\test_onb_master_p2_photos_and_public.py -k "public_statement_selects_estates_by_explicit_publication or public_detail_allows_explicitly_published_demo_classified_estate or public_detail_still_hides_private_demo_estate" -q` — **3 passed**.
- `C:\Users\garah\AppData\Local\Programs\Python\Python312\python.exe -m pytest backend\tests\test_onb_master_p2_photos_and_public.py -q` — **18 passed, 8 skipped**; skipped tests require the configured test database.
- `C:\Users\garah\AppData\Local\Programs\Python\Python312\python.exe -m compileall -q backend\app` — **passed**.
- `C:\Users\garah\AppData\Local\Programs\Python\Python312\python.exe -m flake8 backend\app\property\repositories\estate_repository.py backend\app\property\services\public_directory_service.py backend\tests\test_onb_master_p2_photos_and_public.py --count --select=E9,F63,F7,F82 --show-source --statistics` — **passed, 0 selected violations**.
- `git diff --check` — **passed**.
- The repository-configured `backend\venv\Scripts\python.exe` was absent; validation used the installed Python 3.12 interpreter instead.
- The live database's flags for the five estates could not be read without database access, and production was not changed or redeployed. Deploy the backend change, then verify `/api/v1/public/estates?page=1&page_size=12` returns the five intended public records. If it does not, inspect the exact estate identities and `is_public` values read-only before any data repair.
