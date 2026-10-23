# VALORA — UX experience completion batch

**Owner-approved scope:** Complete the product experience, not just fix isolated defects.
**Branch:** `codex/valora-experience-completion`
**Primary brief:** `docs/CODEX_UX_REDESIGN_BRIEF.md`
**Working mode:** implementation-first, token-conscious. Do not spend the session budget running broad test suites repeatedly.

## Mission and definition of done

Deliver a coherent, polished, intuitive VALORA experience that respects its existing GitHub-inspired light-purple identity. Do not stop at a plan, report, mockup, component gallery, or cosmetic reskin. Inspect the current code, implement the highest-impact work end-to-end, and leave a concise handoff explaining what is implemented and what genuinely requires external credentials or live runtime access.

The product should feel like one considered experience, not disconnected routes and dashboards. Borrow principles—not layouts—from Airbnb (purposeful photo-led discovery), Linear (focus and responsive interaction), and editorial product sites: clear hierarchy, deliberate whitespace, purposeful imagery, context-aware navigation, progressive disclosure, and interaction feedback. Do not copy another product or use the earlier green/black generated mockup as visual authority.

## Token-budget protocol — mandatory

1. Read this batch, `AGENTS.md`, `docs/CODEX_UX_REDESIGN_BRIEF.md`, the relevant progress reports, and the applicable installed design skills. Inspect the current working tree and existing changes first. Preserve user changes.
2. Use existing design skills and installed tools; do not spend time installing a pile of overlapping skills or researching unnecessarily. Read the existing design contract if present. If documentation named in `AGENTS.md` is absent, record that once and proceed using available docs.
3. Spend at least 80% of the work budget on implementation, not test execution, planning, or status narration. Do not run broad tests or browser suites during exploration. Do not rerun the same failing command repeatedly.
4. Implement in coherent batches: trace the critical flows, make the changes, review the diff, then run only one focused validation pass near the end. Prefer build/type/lint and a few relevant tests. Do not start a full Playwright suite unless implementation is complete and sufficient budget remains. Never let repeated tests consume the session budget.
5. If browser tooling, production credentials, database access, or provider configuration is unavailable, do not loop. Implement what can be safely done from source, write explicit manual verification steps, and move on.
6. Do not fabricate test results, live data, screenshots, database state, successful AI responses, or deployment verification. Separate implemented, locally verified, and externally blocked.
7. Keep a short running checklist, then update the progress report once near the end. Do not stop to write intermediate progress reports after every tiny change.

## Product experience principles

### Visual identity and storytelling
- Preserve and consistently use VALORA's existing light-purple brand identity and current design tokens. Do not introduce a new green/black palette. Avoid arbitrary gradients, excessive pills, generic dashboard kits, repeated nested cards, decorative metrics, fake charts and unsupported claims.
- Use architectural/community imagery purposefully where it helps users recognise a complex, understand place, or create an inviting sense of context. Prefer actual published estate imagery and existing approved assets. Use tasteful placeholders only when an image is genuinely absent; label no fake data as real. Handle loading, missing images, alt text, crop, and responsive sizing.
- Give each page an editorial hierarchy: one clear purpose, a dominant next action, meaningful content rhythm, concise copy, selective imagery, and restrained supporting detail. Do not scatter features randomly across a dashboard.
- Build a coherent shared system (type scale, spacing, surfaces, borders, focus, motion, responsive breakpoints) by extending existing primitives/tokens rather than adding competing design systems.

### Interaction and progressive disclosure
- Navigation drawers/panels should open when explicitly invoked, close with an obvious control and Escape, support outside click where appropriate, trap/restore focus for modal dialogs, prevent background scroll when modal, and preserve the user's task/context.
- Secondary controls, filters, evidence detail, advanced options, and less-frequent actions should appear contextually, not permanently occupy the primary screen. Use graceful transitions that respect `prefers-reduced-motion`, and never use animation to conceal latency or state.
- Every interactive control must have a meaningful outcome, feedback, disabled/loading/error states where appropriate, and accessible name/focus state. Do not ship dead buttons, fake links, or decorative controls that imply functionality.
- Handle loading, empty, partial-data, error, and success states intentionally. Do not let an optional briefing or panel failure blank an otherwise useful page.

### Resident journey
After login, a resident should immediately understand:
1. which estate context they are in;
2. the most relevant open request(s) and what happens next;
3. important estate notices;
4. the clear next action (e.g. report an issue or view a request);
5. where to see detailed Estate Health/Living Score without duplicating the full score everywhere.
Keep resident actions and information distinct from HOA operational controls. Make request creation, detail, status, and return navigation coherent. Carry selected estate context into registration/access requests using server-validated IDs; URL/client state is context only, never authorization.

### HOA management journey
The HOA portal must be rebuilt around tasks and operational decisions, not a pile of same-weight cards:
1. urgent exceptions and overdue/high-impact issues;
2. the next action and direct path to the complaint/incident/work order;
3. a compact estate health summary;
4. work requiring follow-up and operational trends;
5. deeper Living Score methodology/history and Intelligence when called upon.
Use meaningful visual hierarchy and restrained, selective visualisation. Remove the redundant Living Score widget from the global sidebar; detailed score belongs in Estate Health, with at most one compact contextual summary on the relevant dashboard. Avoid repeating the same metric in sidebar, dashboard, and page header.

### Service provider journey
A provider with valid estate membership must reach the provider workspace, not resident or HOA views. Make assigned work, due/overdue status, next action, and completion evidence easy to understand. Enforce existing role/estate permissions; never trust client-provided estate IDs.

### Public discovery and registration
- Homepage should explain VALORA in plain language, invite users to find their complex, and show published complexes near the top with purposeful architectural imagery.
- Make directory filters, pagination, sorting, and regional filtering correct across the complete result set (server-side if supported). Do not filter only the first six items and imply that is the full region.
- Ensure directory cards and detail routes work on direct load/refresh, with clear loading/empty/error states.
- Pass selected estate context through sign-in/register/access-request navigation, while the backend remains the authority for membership and authorization.
- Do not invent listings, metrics, deployment claims, photos, reviews, ratings, or Living Scores.

### VALORA Intelligence and Ask VALORA
- There should be ONE intentional Ask VALORA entry point: the Ask VALORA experience inside the VALORA Intelligence page. Remove the global top-bar Ask VALORA button/spotlight and redundant chat state if they are disconnected/duplicative. Before removal, ensure the page chat is wired to the actual supported AI service.
- Trace the real frontend endpoint, backend endpoint, provider selection, streaming protocol, feature flags, auth, estate scoping, and error semantics. Do not assume a configured provider works just because a code path exists.
- Prefer the existing real streaming LLM endpoint for the page chat. Preserve estate/user role boundaries and multi-turn context; validate messages and handle cancellation, timeout, rate/quota errors, disabled provider, partial streams, and network failures. Never expose secrets or log prompt/credential contents.
- Do not misrepresent deterministic keyword responses as LLM output. If fallback exists, label it honestly and only use it if it remains safe and useful.
- Render model output as structured, readable content—not raw asterisks or an essay-shaped wall of text. Use proper hierarchy for headings, paragraphs, lists, compact callouts, evidence/source details, and contextual follow-up chips/actions. Use icons sparingly and only when they clarify meaning. Safely render links and tables if supported; do not parse model HTML or introduce XSS.
- Follow-up questions should be specific to the current answer and support useful next steps. Keep the user’s prior question/answer context within the conversation and show a clear new-conversation/reset action.
- A failed briefing request must not hide the independently working chat. Show an honest AI unavailable/configuration state when the actual provider is unavailable. Never claim production AI works without testing the deployed service.

### Public data / Musgrave / database
- Trace frontend `VITE_API_BASE_URL`, backend database configuration, public directory endpoint, publication filters, pagination, and applied migrations using source/config names only. Never print or commit secrets, environment values, tokens, or private connection strings.
- Do not hardcode a Musgrave exclusion in frontend code, create fake replacement estates, indiscriminately change flags, or delete estate records. The unwanted record must be identified by database identity in the correct environment before any data mutation. Preserve operational history. If live database access is unavailable, implement a correct source-level fix if established, and document the precise read-only checks required to identify the cause.
- Confirm the public API uses the intended configured backend and does not silently fall back to localhost in production. A client-side frontend never connects directly to Neon; backend connects to PostgreSQL.
- Keep demo estates clearly private/non-public and never represent fictional seed records as live. Do not silently change unrelated production data.

## Execution order

### A. Confirm repository state and critical defects
Read relevant routes, `AppShell`, `TopBar`, `Sidebar`, `ValoraChatContext`, Ask VALORA components, Intelligence route/service, Landing, directory/profile routes, registration/access request, and the resident/HOA/provider dashboards. Inspect the current tree before assuming any earlier audit is still true.

### B. Fix integration and trust blockers first
- Resolve duplicate/disconnected Ask VALORA entry points and connect the Intelligence page to the correct actual backend path.
- Remove the duplicated sidebar Living Score widget without removing the detailed Estate Health experience.
- Fix actual public directory API configuration/pagination/filtering defects demonstrated by code.
- Preserve roles, estate authorization, API contracts and operational history.

### C. Deliver the experience (not only fixes)
- Redesign resident and HOA portal hierarchy based on the task priorities above.
- Ensure provider route and tasks remain role-specific.
- Refine public discovery, complex profile and estate-aware onboarding.
- Apply purposeful visuals, responsive editorial layout, shared purple visual tokens, accessible progressive disclosure, and complete interaction states.
- Refine Intelligence chat answer layout and streaming/loading/error/follow-up UX.
- Inventory disconnected prototype routes; do not expose unfinished functionality as working. Avoid unrelated backend architecture work.

### D. Final validation (one focused pass only)
After implementation, inspect the diff and run one focused pass: frontend production build plus a small set of existing relevant unit tests, if available. Do not run every test suite by default. Do not run Playwright unless it can finish within the remaining budget. If a command fails, inspect its output once, fix only if feasible, and do not repeat expensive broad runs. State any tests not run.

## Acceptance criteria

The batch is complete only when:
- [ ] The shared UI follows VALORA's existing light-purple identity and feels coherent.
- [ ] Homepage and directory make it easy to discover published complexes; no fake data or unsupported claims.
- [ ] Public profile and estate-aware registration/access request form a coherent journey.
- [ ] Resident landing clearly prioritises requests, notices, estate context, and next actions.
- [ ] HOA landing prioritises urgent work and decisions; card overload and duplicated Living Score are removed.
- [ ] Provider users reach the provider workspace with role-correct actions.
- [ ] Ask VALORA has one clear home in Intelligence and uses the actual intended AI service, with safe formatted responses, context, evidence, follow-ups, and truthful failure states.
- [ ] Secondary tools/panels reveal and dismiss gracefully, preserve context, and support keyboard/reduced-motion behaviour.
- [ ] Directory data flow is traced; Musgrave is not hidden through an arbitrary UI hack; no unsafe production data mutation.
- [ ] Focused validation is performed once after implementation, with results reported honestly.
- [ ] A final progress report names implemented changes, validation actually run, external blockers, and remaining work. Stop after this batch; do not start unrelated tasks.
