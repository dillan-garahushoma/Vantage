# VALORA — System-Wide UX Redesign Brief

**Repository:** `dillan-garahushoma/Vantage`  
**Execution branch:** `ux/full-system-redesign`  
**Status:** Owner-approved implementation brief  
**Source of truth:** This document plus `batches/ux-system-wide-redesign.md`  
**Visual reference:** The supplied full-system VALORA concept image is directional inspiration. Attach it to the coding-agent session or place a local copy at `docs/design-references/valora-system-redesign-reference.png`. Do not treat its illustrative data as real.

## Mission

Make VALORA feel like one intentional, polished, responsive product across every route and role—not a collection of pages with similar card layouts. Execute the implementation, use the available browser continuously, and verify the experience. This is not a request to produce another critique, prompt, or mockup.

VALORA is an AI-powered Property Health Intelligence Platform for South African private residential estates. It turns operational evidence into estate-health understanding and supports the real work of residents, HOA administrators and service providers.

The target experience combines:
- the confidence and photo-led discovery of a well-crafted property product;
- the focus, hierarchy and responsive interactions of high-quality modern software;
- purposeful imagery, editorial storytelling and humane microcopy;
- operational precision, evidence traceability and strong role/estate boundaries.

Do not copy Airbnb, Linear, GitHub or any concept image literally. Preserve VALORA's established light-lavender/violet identity. Existing Overview refinements on the current branch are the baseline to preserve—not a reason to stop improving the rest of the application.

## 1. Mandatory reconnaissance

Before changes:
1. Read `AGENTS.md`, this brief, `batches/ux-system-wide-redesign.md`, `docs/CODEX_UX_REDESIGN_BRIEF.md`, `frontend/DESIGN.md`, and relevant `.agents/skills/` files. Especially inspect the product-design, frontend-design/taste, web-design-guidelines, image-to-code, playwright-cli and quality-gates skills that are actually present. Do not assume a skill exists without checking.
2. Inspect Git status, branch, recent commits and existing diffs. Preserve uncommitted work. Do not reset, clean or overwrite a partner's changes.
3. Start the frontend/backend using repository instructions and inspect the current browser-rendered product. The browser is the authority for what users see.
4. Inventory every route and nav item by role. Distinguish live screens, redirects, placeholders and legacy/disconnected screens.
5. Run baseline build/tests and record exact results, including skipped tests and blockers.
6. Inspect the existing resident Overview independently. The administrator Overview has received a visual update, but do not assume the resident Overview was upgraded to the same quality. Keep any Overview that is already good out of scope except for verified defects or required integration changes.
7. Map each major view to real API data, role permissions, loading/error/empty states and available actions.

Do not begin a wholesale visual rewrite before this audit. Do not stop after the audit: proceed into implementation.

## 2. Route inventory to inspect

Verify this list against `frontend/src/App.jsx` and `frontend/src/routes/` before editing.

### Public and access journeys
- `Landing.jsx`
- `PublicEstates.jsx`
- `PublicEstateDetail.jsx`
- `Methodology.jsx`
- `Contact.jsx`
- `Login.jsx`
- `Register.jsx`
- `PasswordRecovery.jsx`
- `Welcome.jsx`
- `WelcomeSuccess.jsx`
- `Join.jsx`
- `RequestAccess.jsx`
- Provider application/invitation/waiting routes: `ProviderApply.jsx`, `ProviderAcceptInvitation.jsx`, `ProviderWaiting.jsx`

### Resident-facing workspace
- Resident Overview in `Dashboard.resident.jsx`: audit; preserve if already satisfactory.
- Complaints/request reporting and request tracking.
- `Announcements.jsx`
- `Notifications.jsx`
- `EstateHealth.jsx`
- `Intelligence.jsx` with resident-scoped Ask VALORA.
- `Settings.jsx` and other legitimately resident-accessible account/property views.

### HOA administrator workspace
- Administrator Overview in `Dashboard.admin.jsx`: preserve established improvements, except verified defects.
- `EstateHealth.jsx`
- `Intelligence.jsx`
- `Complaints.jsx`
- `WorkOrders.jsx`
- `Incidents.jsx`
- `Properties.jsx`
- `Providers.jsx`
- `Announcements.jsx`
- `Members.jsx`
- `AdminResidency.jsx`
- `AdminSetup.jsx`
- `Notifications.jsx`
- `Settings.jsx`

### Service-provider workspace
- `ProviderWork.jsx`
- Relevant invitation/acceptance and waiting screens.
- Any provider-specific detail, status-update and completion interactions.

### Shared infrastructure
- `AppShell.jsx`, `Sidebar.jsx`, `TopBar.jsx`, `MobileNav.jsx`
- estate selector, account menu, dialogs, drawers, forms, tables/lists, status chips, charts, shared UI tokens and states.
- VALORA Intelligence components: `AskValora.jsx`, `AskValoraSpotlight.jsx`, `AiAnswerRenderer.jsx`, `HealthBrief.jsx`, `SignalField.jsx`, `RecommendationCard.jsx`, and the corresponding services/types/tests.

Some routes may be intentionally redirected, role restricted, or no longer in product scope. Verify them. Do not expose disconnected prototypes just to make the navigation look full.

## 3. Design philosophy: composed surfaces, not interchangeable cards

The app already has a portal shell. The task is to make the content within it feel authored and intentional.

Use the most useful surface for the information:
- **Editorial compositions** for public discovery, estate context and welcoming transitions.
- **Lists and tables** for repeated operational records, requests, jobs, members and complaints.
- **Analytical sections** for the Living Score, pillars, time series and methodology.
- **Timelines** for record history and progress where supported by data.
- **Inline status** beside the relevant record instead of a separate status card.
- **Contextual drawers/details** for investigation and supporting evidence.
- **Focused forms/wizards** for creation and setup.
- **Small metric groupings** only where comparison genuinely supports a decision.

Do not remove all cards; stop using cards as the default wrapper for everything. Fewer, more meaningful containers with strong spacing and typography are preferable to a sea of equal-weight tiles.

Each screen should establish:
1. page purpose;
2. primary task or finding;
3. relevant records and evidence;
4. one clear next action;
5. secondary details available when requested.

Maintain clear visual hierarchy. Separate shell chrome from page content. Avoid oversized blank sections, excessive eyebrow labels, repeated explanatory paragraphs, ornamental numbers and generic gradient decorations.

## 4. Visual identity and quality

Preserve the existing VALORA light-lavender/violet identity and inspect `frontend/DESIGN.md` for the design contract. Reuse and refine existing tokens; do not create a competing palette.

- Violet is the brand/action accent; semantic colours communicate status and risk.
- Use readable typography, line lengths, spacing and consistent page rhythm.
- Prefer fine dividers, subtle surfaces and restrained shadow over borders around every paragraph.
- Architectural photographs must add estate identity or contextual meaning. Use suitable existing assets and validate crop, aspect ratio, fallback and loading behaviour.
- Never imply generic artwork is an actual selected estate. Never invent live estate data, scores, evidence, prices, reviews or operational claims.
- Use appropriate Lucide icons that explain actions or meaning; icons must not replace accessible labels.
- Animations should clarify state changes, be restrained, and respect `prefers-reduced-motion`.
- All controls must be keyboard accessible, have visible focus, and use appropriate semantic HTML and contrast.

No generic AI-looking reskin. Make page composition decisions based on purpose.

## 5. Role-specific experience requirements

### Resident
The resident should feel welcomed into their community and immediately understand their own requests, status updates, relevant notices and available estate-health information. Reporting an issue and returning to track it should be straightforward. Do not expose other residents' records or internal HOA work queues.

### HOA administrator
The administrator needs an operational workspace. Prioritise overdue/high-severity issues, evidence, assignment, work orders, incidents and permitted actions. Record lists should be scannable and functional. The administrator should be able to investigate a record and return to the original context without losing place. Preserve confirmation for consequential actions.

### Service provider
The provider needs assigned jobs, instructions, authorised access details, due dates, status and completion requirements. Do not reuse resident UI or expose estate-wide HOA intelligence. Expose only the minimum resident/unit data authorised for each assigned job.

### Role separation is a security requirement
Determine the role and estate membership from authenticated server-side context. Frontend hiding and LLM prompts do not enforce access control. Confirm authorised data is filtered before it reaches model context, stream tokens, citations, history, saved briefings and follow-up responses. A client-supplied role, estate identifier or record reference is never proof of access.

## 6. Page-specific intent

### Public discovery and profile
Tell a clear story about VALORA; bring genuine published complexes near the top; use photo-led listing layouts and meaningful location/unit information where the API provides it. On profile pages, make details, published health information and joining/request-access paths easy to understand. Carry selected-complex context through registration where supported, without treating URL/client state as authorisation.

### Authentication and onboarding
Make sign-in, registration, recovery, join-code, access-request, administrator setup and provider invitations feel like a guided journey. Clarify required fields, validation, errors and what happens after submission. Avoid redundant steps but preserve membership approval and invite security.

### Estate Health
Treat this as an analytical destination, not a duplicate Overview. Make the stored Living Score, as-of date, interpretation, five actual pillars, published weights, history, supporting evidence and methodology easy to explore. Use stored snapshots only. Backend remains the authority for calculations.

### Complaints, work orders and incidents
Use scannable records, clear status/severity, relevant dates and ownership. Filters/sorts must work and reflect backend capabilities. Record details should show activity/evidence and available actions in context. Distinguish a resident's own request view from the HOA's estate-wide operational view.

### Properties, providers, residents and residency management
Prioritise finding, reviewing and acting on the real record. Use good list/detail patterns, helpful filters and clear states. Avoid dashboards full of summary cards on pages whose primary job is record management.

### Announcements and notifications
Make unread/read status, dates, importance, content and permitted actions clear. Keep creation/editing flows distinct from how residents consume announcements. Do not invent notification delivery states.

### Settings and setup
Group settings by mental model, explain consequential changes before saving, show save/error feedback, and organise setup into comprehensible steps. Keep complicated secondary configuration out of the main navigation unless it is a core recurring task.

### VALORA Intelligence
Build a distinctive analysis workspace, not a chatbot with surrounding cards. Make findings, evidence, implications, actions and follow-up investigation readable and contextual. A simple question deserves a simple answer; a complex analysis can be structured into a key finding, evidence, why it matters, justified next action and contextual follow-ups. Never expose raw Markdown or undifferentiated essay walls. Do not invent citations, metrics or confidence values.

Intelligence must have three different authorised purposes:
- **HOA:** estate-wide operational trends, incidents, complaints, overdue/unassigned jobs, provider performance and management actions.
- **Resident:** their own authorised requests, recorded updates, published notices/rules, and permitted estate-health explanations.
- **Provider:** their own assigned jobs, relevant instructions, authorised access details, deadlines and completion requirements.
Resident/provider content must never include other users' private records or HOA-only operational assessments. Verify this both in backend integration tests and UI tests.

## 7. Interaction design requirements

Implement only interactions that improve the task:
- panels, menus, dialogs and drawers appear when requested and close predictably;
- focus is moved into opened dialogs when appropriate, returned to the triggering control on close, and supported by Escape where appropriate;
- mobile navigation closes after navigation and does not leave the page trapped or obscured;
- form actions have loading, validation, error, success and disabled feedback;
- details/filters/expansion controls actually function;
- AI streaming preserves context and presents partial output without layout jumps;
- empty states explain a useful next action;
- links lead to working routes and buttons do not pretend to work.

Preserve navigation context when it is useful. Avoid motion or controls that exist only for decoration.

## 8. Engineering and data guardrails

- Preserve API contracts unless a demonstrated gap requires a change; document and test intentional changes.
- Keep business rules in backend services, not React.
- Never calculate Living Score, trends, ratios or operational claims independently in the frontend when the backend owns them.
- Respect estate tenant boundaries, membership and role permissions for every read/write.
- Do not replace production data with hardcoded visual fixtures.
- Do not show null/unavailable values as zero.
- Keep demo data unmistakably separate from live estate claims.
- Inspect legacy/disconnected routes and either keep them out of navigation or give a clear redirect/availability treatment consistent with product scope.
- Avoid dependency proliferation and broad unrelated refactors.

## 9. Execution sequence

Work in small, reviewable phases. Do not attempt to rewrite the whole codebase in one unreviewable pass.

**Phase 0 — Baseline and inventory**
- Verify routes/roles, existing Overview quality, current branch changes, API data, tests and browser states.
- Record current visual defects and identify incomplete screens.

**Phase 1 — Shared design primitives and shell**
- Improve design tokens only where needed.
- Refine shared panels, list rows, forms, tables, drawers, status display and mobile navigation.
- Keep changes backward compatible and inspect every route affected by shared components.

**Phase 2 — Resident pages**
- Audit resident Overview and preserve it if already satisfactory.
- Refine resident-accessible non-Overview pages and journeys.
- Verify report issue → request detail/status → return to context, announcements/notifications and resident-scoped Intelligence.

**Phase 3 — HOA operational pages**
- Refine Estate Health, Intelligence, Complaints, Work Orders, Incidents, Properties, Providers, Announcements, Members, Residency, Notifications, Settings and setup.
- Keep record operations primary; use secondary panels for investigation.

**Phase 4 — Provider pages**
- Refine assigned-work list, job detail, instructions and completion flow, with role-scoped data.

**Phase 5 — Public discovery and onboarding**
- Refine homepage, directory, profile, auth, join and access request.
- Verify discovery → profile → account/access journey.

**Phase 6 — Browser acceptance and consolidation**
- Run tests, inspect actual screenshots and correct defects.
- Verify all changed journeys and role separation.
- Update progress reports and acceptance issues with evidence.

A phase may be reordered for dependency reasons, but it may not be declared complete without its stated verification. If a screen is already good, verify it and move on rather than changing it for the sake of change.

## 10. Browser verification and quality gates

Use the available browser/Playwright tooling. Inspect the real rendered app; do not only rely on static code or component tests.

For each changed route:
1. exercise it at desktop (~1440px), tablet and mobile (~390px);
2. capture screenshots and compare hierarchy, spacing, typography, image crop and responsive behaviour;
3. test the primary interaction and a secondary/detail interaction;
4. verify loading, populated, empty, insufficient-data, error and recovery states as relevant;
5. inspect console errors and network failures;
6. check keyboard/focus behaviour, reduced motion and visible control labels;
7. run the relevant unit/E2E tests and production build.

Run browser tests in bounded, observable batches. Capture the real exit status; investigate failures instead of reporting timeouts as passes. Use deterministic test fixtures only for tests, never as evidence of live production content.

At minimum, capture the final resident non-Overview page, HOA Estate Health, HOA Intelligence with a populated answer and supporting evidence, a complaint/work-order detail surface, provider assigned work, public directory/profile and mobile navigation. Capture the Overview pages as regression screenshots to ensure they were not damaged.

## 11. Definition of done

The task is complete only when:
- every active visible route has a deliberate, consistent design quality;
- resident, HOA and provider interfaces are distinct in purpose and authorised data;
- Overview improvements remain intact unless a verified defect required a fix;
- record-heavy pages are task-focused and not generic card grids;
- contextual surfaces and forms work at desktop/mobile;
- AI answers are clearly structured, contextual and secure;
- real data is used and demo/live distinctions remain accurate;
- relevant tests and production build pass, with skips reported honestly;
- screenshots from the actual application have been inspected at desktop, tablet and mobile widths;
- the GitHub UX acceptance checklist and progress report list what changed, what ran, actual browser evidence and remaining blockers.

## 12. Progress report

Write `docs/progress/ux-system-wide-redesign.md` as work progresses and at completion. Include:
- routes changed and user journey improved;
- files changed and major interaction decisions;
- tests/build/browser commands and exact outcomes;
- screenshots captured and viewports actually inspected;
- skipped tests, environment limitations and remaining defects;
- any intentional deviation from this brief.

Never claim browser, accessibility or integration verification that was not performed.

**Final directive:** Curate the experience around user intent, implement it in the real app, verify it in the browser, and keep moving through the entire agreed scope. Do not stop after another critique or design proposal.
