# VALORA system-wide UX redesign — execution batch

**Canonical branch:** ux/full-system-redesign  
**Master specification:** docs/UX_SYSTEM_WIDE_REDESIGN_BRIEF.md  
**Existing context:** docs/CODEX_UX_REDESIGN_BRIEF.md, frontend/DESIGN.md, HANDOFF_FRONTEND.md, HANDOFF_BACKEND.md  
**Acceptance tracker:** GitHub issue #6  
**Execution mode:** Browser-first, implementation-focused; preserve user/partner changes.

## Mission

Execute the system-wide VALORA experience redesign in the master brief. Do not produce another plan or another assessment that pages are card-driven. Implement the actual user experience across all in-scope routes and role-specific portals, verifying the working browser throughout.

The Overview UI received a recent visual pass on the parent commit. Preserve it unless browser verification reveals a concrete defect. Explicitly audit the resident Overview separately; do not assume its quality matches the HOA Overview.

## Required start-up

1. Read AGENTS.md and the master specification end-to-end.
2. Read frontend/DESIGN.md and the relevant frontend design, browser and quality-gate skills present in .agents/skills/.
3. Inspect current git status and diffs; never reset, clean or discard uncommitted changes.
4. Run the application and inspect the actual browser state before editing.
5. Inventory all routes in frontend/src/App.jsx, navigation links by role, relevant API/service implementations and the current test coverage.
6. Record the baseline browser screenshots and build/test outcomes. Distinguish existing failures from regressions.

## Execution order

### A. Shared system and route inventory
- Check the shell, navigation rail, top bar, estate selector, account menu, mobile navigation, global typography/tokens and reusable surfaces.
- Identify disconnected/legacy routes and any visible navigation link that leads to an unfinished screen or 404.
- Keep the shared shell calm and consistent; allow each page to use the layout that best fits its task.

### B. Resident portal
- Audit the resident Overview separately; preserve if already fit for purpose.
- Redesign all resident-accessible non-Overview screens: own complaints/requests, announcements, notifications, Estate Health, Intelligence, settings and other supported resident pages.
- Make report → status → details → return-to-context coherent and welcoming.
- Resident Intelligence is a personal estate assistant. It must not reveal other residents' data or HOA-only operational analysis.

### C. HOA administrator portal
- Preserve the existing HOA Overview unless a verified problem is found.
- Redesign Estate Health, Intelligence, Complaints, Work Orders, Incidents, Properties, Providers, Announcements, Members, Residency, Notifications, Settings and setup.
- Use dense, scannable lists/tables for record-heavy workflows, analytical layouts for Estate Health and contextual detail surfaces for investigation.
- Ensure evidence, assignment, status, work-order actions and record links operate on actual permitted records.

### D. Service-provider portal
- Create/maintain a separate work-focused experience centred on the provider's assigned jobs, relevant instructions, due dates, authorised access details and completion workflow.
- Do not show resident dashboard content or HOA-wide records. Respect provider/estate membership restrictions on both client and server.

### E. Public discovery and onboarding
- Verify and refine homepage, public estate directory/detail, methodology, sign-in, registration, password recovery, join-code, request-access and provider onboarding.
- Preserve selected-estate context where useful without treating URL/client state as authorisation.
- Use real published estates and purposeful architectural imagery. Do not fabricate live content.

### F. VALORA Intelligence and role separation
- Follow the Intelligence section of the master brief and the image reference supplied to the coding-agent session.
- Make AI output scannable, structured, and proportionate to the question. Never show raw Markdown or essay-like walls of text.
- HOA intelligence: authorised estate-wide trends, issues, incidents, work orders and management actions.
- Resident intelligence: own authorised requests plus permitted published estate information.
- Provider intelligence: own assigned work and minimum information needed to perform it.
- Verify server-side filtering before data enters model context and across streamed responses, evidence/citations, historical briefings and follow-up turns. UI hiding and prompts are not access control.
- Do not invent APIs, evidence, metrics, confidence values, history or unsupported actions.

## Design standard

Follow the existing VALORA light-lavender/violet identity and frontend/DESIGN.md. Use purpose-built editorial compositions, record lists/tables, status-in-context, timelines, charts only where actual data makes them useful, and contextual drawers/forms. Avoid interchangeable card grids, nested cards, decorative metrics, random imagery and dead controls.

Every page must make its purpose and next useful action obvious. Contextual panels should open and close naturally, maintain task context, support keyboard/focus behaviour, and adapt to mobile. Respect prefers-reduced-motion.

## Browser and test requirements

Use the available browser/Playwright environment. Run the application, inspect actual rendered screens, and interact with real routes. Do not claim browser verification from source code or component tests alone.

Capture before/after screenshots where possible at:
- Desktop: approximately 1440px
- Tablet: a real tablet-width viewport
- Mobile: approximately 390px

At minimum inspect resident non-Overview screen, HOA Estate Health, HOA Intelligence with populated response/evidence, complaints/work-order details, provider assigned work, public directory/profile, authentication/access journey and mobile navigation. Capture both Overview pages as regression comparisons.

Test populated, loading, empty, insufficient-data, error and retry states as relevant. Inspect console/network failures, keyboard/focus, responsive overflow and actual primary actions. Run focused tests/build and relevant backend/contract/role authorization tests. Do not count skipped or timed-out tests as passing. Execute full suites only when there is enough time and the environment can return an observable result.

## Progress and stopping rules

Write the ongoing report to docs/progress/ux-system-wide-redesign.md. Report implemented work, files changed, commands and exact test results, browser routes/viewports actually inspected, screenshots actually captured, failures/skips and unresolved limitations.

Work incrementally and review diffs. Do not redesign the Overview pages without evidence. If a page is already good, verify it and move on. Do not stop after a plan, a source audit, a visual mockup or a successful build. Continue through route groups in the order above; if the session reaches its budget, finish a coherent slice and give a precise handoff naming the next route group. Never falsely mark the entire system complete while routes remain untouched.

## Definition of done

The in-scope pages are intentionally designed and consistent; resident, HOA and provider workspaces have distinct purposes; all visible controls and important journeys work; Intelligence has verified role-specific data boundaries; desktop/tablet/mobile screenshots have been inspected; tests/build outcomes are truthful; and issue #6 and the progress report reflect actual evidence.
