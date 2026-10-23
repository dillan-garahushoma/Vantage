# VALORA Experience Redesign — Codex Execution Brief

**Status:** Owner-approved product direction  
**Repository:** \`dillan-garahushoma/Vantage\`  
**Primary objective:** Turn VALORA into a polished, trustworthy, editorially designed property-health product with coherent public discovery, role-specific workflows, and a well-designed AI experience.

This is an execution brief, not a request to merely write another plan. Audit the current implementation, identify what is real and reusable, then deliver the redesign in small, testable phases. Do not rewrite the backend or invent product capabilities just to make the UI look richer.

## 1. Product intent and quality bar

VALORA helps people understand how a South African residential complex is being managed. It turns operational evidence—maintenance complaints and their resolution, work orders, security incidents, provider performance and resident feedback—into estate-level health intelligence and a Living Score.

The experience must communicate that story without asking visitors to understand system terminology first.

The desired bar is a considered digital product: strong editorial hierarchy, architectural imagery, deliberate typography, clear content rhythm, real listings, crisp interactions and restrained colour. Airbnb is an inspiration for photo-led discovery, not a marketplace template to copy. Dominus Investments is a useful reference for confident editorial storytelling and intentional composition. Linear is a reference for focus and interaction clarity, not a mandate to make every screen a monochrome dashboard.

**Do not preserve a weak design just because it already exists. Do preserve correct domain behaviour, API contracts, tenancy boundaries, role restrictions and tested workflows.**

The work must not be a generic Tailwind reskin. Make explicit choices about user intent, hierarchy, page composition and content before coding.

## 2. Start by reconciling the repository

Before making changes:

1. Read root \`AGENTS.md\`, this brief, \`.agents/skills/valora-product-design/SKILL.md\`, and the AI-conversation skill. Follow the existing architecture, security and test rules.
2. Inspect current git status and branch. Never discard or overwrite user changes. Work in the existing Codex working tree; do not reset or clean the repo.
3. Inspect the actual frontend routes and components, including \`App.jsx\`, \`Landing.jsx\`, \`PublicEstates.jsx\`, \`PublicEstateDetail.jsx\`, \`Dashboard.admin.jsx\`, \`Dashboard.resident.jsx\`, \`Dashboard.jsx\`, \`EstateHealth.jsx\`, \`Intelligence.jsx\`, \`AskValora.jsx\`, \`AskValoraSpotlight.jsx\`, \`HealthBrief.jsx\`, \`AppShell.jsx\`, navigation/layout components, and current UI primitives.
4. Read the actual API response types and service implementations used by those components before changing any data presentation.
5. Run existing frontend checks and note the baseline. Distinguish failures that existed beforehand from failures introduced by the redesign.
6. Create a short route/persona audit in the progress report, then execute the phases below. Do not stop after returning a plan.

Work incrementally. Each phase needs focused tests, visual verification and a concise report of changed files, tests run and remaining risks. Do not make an enormous unreviewable rewrite in one step.

## 3. Confirmed issues to address

The earlier repository audit found the following; recheck each against the current working tree before fixing it because the repository may have changed:

- The app has \`PublicEstates.jsx\` and \`PublicEstateDetail.jsx\`, and public navigation links to \`/estates\`, but \`App.jsx\` did not register \`/estates\` or \`/estates/:id\`. The screenshot showed the resulting 404.
- \`Dashboard.jsx\` sends the administrator role to \`AdminDashboard\` and all other roles to \`ResidentDashboard\`. A service provider must not get the resident dashboard.
- The current landing hero uses “South African private estates” and “MVP — pilot deployment” badges, a static estate-plan illustration and dashboard-like metrics. This foregrounds internal positioning instead of the product's purpose.
- The current admin dashboard places many sections inside repeated boxed surfaces. The resident dashboard repeats Living Score explanation and prioritises a generic score panel over the resident's issue journey.
- \`Intelligence.jsx\` and the Ask VALORA components need a deliberate information design for AI output. Long, raw Markdown-like text with visible asterisks or repetitive lines is unacceptable.
- The E2E smoke test was noted to expect an old hero heading; the mobile sweep can pass a 404 because it measures overflow instead of asserting that the intended route rendered. Verify whether these tests remain stale.
- \`backend/app/seed_demo.py\` was noted to seed fictional complexes with \`is_demo=False\`, \`is_public=True\`, and \`show_living_score=True\`. The directory filters by publication status, while score origin uses the demo flag. Trace the real seed/deploy behavior and correct classification so fictional sample records cannot be represented as live estates. Use demo records for visual fixtures only, or label demo data unambiguously in a controlled demo experience. Do not silently change production publication or score behaviour without tests.
- Extra pages such as \`Financial.jsx\`, \`Community.jsx\`, \`ProviderPortal.jsx\`, and \`PropertyWorkflows.jsx\` may be legacy, disconnected or sample-only. Classify them; do not surface unfinished screens or fake interactivity as product functionality.

These are audit leads, not permission to assume the current branch is unchanged. Prove each defect before altering it.

## 4. Curate the public user journey

### 4.1 Homepage: discovery first

The homepage must quickly answer:
- What is VALORA?
- Why should a resident or estate stakeholder care?
- Can I find my complex?
- What should I do next?

Design direction:
- Remove “South African private estates” and “MVP — pilot deployment” hero badges. Remove “Live operational deployment” unless it is backed by a genuine, verifiable operational record and labelled accurately.
- Replace the static site-plan-as-hero with a strong architectural/community photograph or an intentional photo composition. Preserve authentic image sources and appropriate image rights. No broken images, generic gradient blobs or decorative charts with no purpose.
- Use editorial copy with a clear headline, one specific explanatory paragraph and one primary CTA such as “Find your complex”. Provide a secondary sign-in or resident-access path.
- Put published complex discovery near the top of the landing page—immediately after the hero, not behind a navigation link and a separate directory landing page.
- The first screen should not be full of internal labels, model weights or technical explanation. Methodology belongs farther down the page and on its own page.
- Tell the product story with a small number of sections and changing composition: strong headings, concise text, image, divider, list or timeline where appropriate. Avoid the same three-card grid for every section.
- The footer should support the journey, not repeat internal architectural language.

### 4.2 Published complex catalogue

Reuse the real public-directory API and components. Do not create a separate fake catalogue for marketing.

- Show real published complexes returned by the public API.
- Build photo-first listing tiles with complex name, suburb/city/province, unit count and a short description where available.
- Display a Living Score only when the estate explicitly publishes it and a valid stored score exists. Never invent ratings, property prices, availability, reviews, locations or performance metrics.
- Support search, loading, error, no-results and no-published-estates states with clear hierarchy and recovery paths.
- Keep cards as a coherent browsing surface: image leads, details follow, click/tap opens the actual profile.
- Responsive layout must feel considered on mobile, tablet and desktop.

### 4.3 Complex detail → account → access

- The public complex profile should lead with photography, name, location and unit count, then a clear story/about section, published operational-health information if available, and the join/access path.
- Preserve the privacy boundary: never publish unit-level data, resident names/contact information, private complaints, incident details or score components that the API is not designed to expose.
- Carry the selected complex forward as navigation context when visitors continue to registration or request access. Avoid forcing visitors to search for it again.
- Do not treat URL parameters or client state as proof of estate membership. The API must continue to authorise every protected operation.
- Explain the two residency paths simply: redeem a code from the estate office, or request access for HOA approval. Set expectations about approval without making the person repeat information.
- Fix route registration and verify navigation through the real router, not only isolated component tests.

### 4.4 Target public flow

\`\`\`mermaid
flowchart TD
    A[Editorial homepage] --> B[Browse or search published complexes]
    B --> C[Photo-led complex profile]
    C --> D{Next step}
    D --> E[Create account or sign in]
    D --> F[Redeem join code]
    E --> G[Request access to the selected complex]
    G --> H[HOA reviews request]
    F --> I[Membership resolved by API]
    H --> I
    I --> J[Correct role-specific workspace]
\`\`\`

## 5. Design role-specific dashboards around tasks

One shell may be shared, but the workspaces must not be copies of one another. Each page needs one clear primary purpose, a restrained number of high-value signals, and a visible path to the next action.

### 5.1 HOA administrator: operational overview

Primary question: **What needs management attention now, and what should I do next?**

Suggested hierarchy:
1. Estate identity and compact context, with relevant global actions.
2. A prioritised exceptions/work queue: urgent or overdue complaints, unassigned work, unresolved incidents, failed or delayed jobs. Each item must connect to the real record and use actual status/severity.
3. A concise Living Score summary with status, as-of date, trend only when supported by stored snapshots, and a path to the health analysis.
4. At most a few decision-relevant measures (for example open issues, resolution performance and work orders in flight) with definitions/context. Do not show four equally loud cards just because four numbers are available.
5. A compact recent activity or announcements section only if it changes what an administrator should do.

Move full pillars, long score explanations and historical charts to Estate Health. Move full complaint/work-order inventories to their dedicated pages. Intelligence should add useful judgement, not simply repeat the dashboard.

No duplicated sections, oversized empty boxes, unlabelled charts or repeated explanatory paragraphs. Exceptions should be visually prominent because their state matters, not because every component is given a coloured background.

### 5.2 Resident: my home and my requests

Primary question: **What is happening with my issue, and is there anything I need to do?**

Suggested hierarchy:
1. Friendly estate context and one obvious maintenance/reporting action.
2. A compact “Your active requests” list with clear current statuses and next-step explanations.
3. Important estate announcements/alerts, when present.
4. A concise published Living Score/estate-health summary, with an explanation and link to detail rather than a large duplicate health dashboard.
5. Empty states that teach the one next action without repeating the entire scoring methodology.

Do not let an estate-wide score crowd out the resident's own request. The resident sees only records their role is authorised to see.

### 5.3 Service provider: assigned work

Primary question: **What work is assigned to me, what is due, and how do I progress it?**

- Route service providers to a provider-specific overview or \`My work\`, not \`ResidentDashboard\`.
- Prioritise assigned/in-progress jobs, due dates, job references, status and any recorded completion evidence.
- Provide actions matching the API state machine and current permissions: start work, submit completion notes, complete work where allowed.
- Never show a resident-only complaint CTA as the provider's primary action.
- Keep a visible, meaningful empty state when nothing is assigned. Do not display sample jobs as real assignments.

### 5.4 Estate Health

Keep this as the analytical destination for the stored Living Score, component pillars, history, calculation date/version and methodology. It should explain what evidence is available and where data is insufficient. Never calculate or “smooth” score values in React; the backend remains authoritative.

### 5.5 VALORA Intelligence

This should be a decision-support workspace, not another oversized dashboard of cards.
- Lead with a concise headline and the most consequential finding.
- Show why it matters, its measured basis and the relevant time window.
- Present a short, ranked list of recommendations with evidence/source details and a human-controlled next action.
- Use detail drawers/expandable sections for supporting records. Keep the main reading experience scannable.
- Distinguish stored briefings from answers based on current records and label generated AI content accurately.
- Maintain role-safe output: residents and providers must never receive administrative-only record details or recommendations.

## 6. Critical requirement: redesign AI answer presentation

The AI feature currently looks like an essay: visible asterisks/Markdown characters, paragraph after paragraph, and weak visual variation. Do not ship that again.

Audit \`AskValora.jsx\`, \`AskValoraSpotlight.jsx\`, \`HealthBrief.jsx\`, \`Intelligence.jsx\`, and the actual API response shape. Implement one reusable, consistent answer renderer where possible instead of four separate styling approaches.

### 6.1 Render structure, not raw Markdown characters

- Never display raw Markdown markers such as \`**bold**\`, leading \`*\`, literal heading hashes, or raw list syntax to the user.
- If the service returns Markdown, render it through a safe React Markdown renderer with explicit component styling and no raw-HTML execution. Check installed dependencies first; if needed, choose a maintained parser such as \`react-markdown\` with \`remark-gfm\`. Do not use \`dangerouslySetInnerHTML\` or enable unsanitised model HTML.
- If the API returns a structured object, render its schema into purposeful interface elements. Do not flatten it into one string just for ease of implementation.
- Preserve meaning, citations/evidence and line breaks. Normalise malformed or repeated whitespace safely; do not aggressively rewrite the model's factual claims.
- Keep typography restrained and readable. Short paragraphs, useful headings, correctly formatted ordered/unordered lists, bold emphasis only where helpful, inline code only for actual technical identifiers, and tables only when they improve comparison.
- A response renderer should support a clean fallback for plain text and unexpected response shapes.

### 6.2 Make long answers scannable

Use variation only when it improves comprehension—not a coloured card around every paragraph.

A good answer may contain:
- **Direct answer / takeaway**: one concise lead at the top when the question permits it.
- **Key finding**: a clearly emphasised statement or metric, but only when it is present in the evidence.
- **Evidence**: a short list of records, dates, statuses or source references.
- **Recommended next action**: one or a small number of clear actions, only when appropriate to the question.
- **Details**: expandable supporting analysis when a longer explanation is genuinely needed.

Use small, consistent Lucide icons for actions or meaning (for example, alert, check, chart, wrench, calendar, source/document). Icons must reinforce labels, not replace them, and must not become decoration on every line. Use semantic typography, dividers and whitespace; do not stack nested cards or use emoji as the primary UI language.

Do not impose this template on every trivial answer. A simple question deserves a simple answer. A complex analysis deserves structure. Keep the primary response compact, and expose deeper evidence when useful.

### 6.3 Follow-up questions must be contextual

- Offer zero to three suggested follow-up prompts when there is a clear next question related to the user's request or the displayed evidence.
- Examples: “Which open issues are driving this?”, “Compare the last 30 days with the previous 30”, “What should the HOA escalate first?”
- Follow-up prompts should be compact buttons/chips with optional meaningful icons, not a new paragraph of suggested questions.
- Clicking a prompt should submit that exact prompt through the existing conversation flow and preserve the required estate/context.
- Do not invent unsupported filters, comparisons or AI capabilities. Verify the backend supports a requested follow-up before presenting it.
- When relevant context is missing, ask one precise clarifying question in the conversation. Do not show generic suggested prompts or ask multiple questions the system can reasonably answer from available records.
- Let users continue typing freely. Show a clear input composer, submit/loading state, error recovery and keyboard behaviour. Do not clear the user's draft on failure.
- Suggested prompts must not be mistaken for facts or already-completed actions.

### 6.4 Evidence, trust and safety

- Clearly distinguish measured estate data, stored score snapshots, generated interpretation, and suggested action.
- Where records support a claim, show dates/status/source references or a route to inspect the records.
- Do not generate metrics or claim certainty unsupported by the returned evidence. Treat null/unknown values as unavailable, not zero.
- Respect role permissions in both the data request and the displayed result; hiding sensitive text in React is not a substitute for backend authorisation.
- If the model or AI service fails, display a clear failure state and allow retry where supported. Do not leave raw tracebacks or Markdown fragments in the UI.
- Avoid a wall of repeated disclaimers, metadata and “here is what I found” filler. State limitations plainly only when they affect interpretation.

## 7. Visual design principles

### Visual language

- Keep VALORA's existing identity recognisable; refine rather than arbitrarily rebrand.
- The public marketing/discovery experience may be more editorial, warm and image-led. Authenticated operational screens should be quieter, dense enough for work, and focused on actions/data.
- Keep a coherent palette with one brand accent and semantic success/warning/critical colours. The existing violet/lavender should be used intentionally rather than on every eyebrow, border, glow and background.
- Prefer fine dividers, typography and whitespace to heavy shadows and boxes.
- Establish a deliberate type scale, line lengths and consistent spacing. Use tabular numerals for scores, dates and counts.
- Use architecture/complex photography purposefully with consistent aspect ratios and high-quality crops. No image should be treated as “live” evidence without a real data relationship.
- Use motion sparingly and honour \`prefers-reduced-motion\`. Maintain keyboard focus and WCAG AA contrast.
- Use semantic HTML landmarks and correct heading order. Interactions must be accessible by keyboard and have visible focus states.

### Explicit anti-patterns

- No endless card grids, card-inside-card layouts or a bordered box for every paragraph.
- No generic hero badges describing MVP status, internal jargon, arbitrary model statistics or fake live-status labels.
- No marketing fluff, unexplained data jargon, repetitive micro-labels or essay-like AI messages.
- No giant numbers without unit, date or useful context.
- No arbitrary purple glow blobs, random gradients, decorative charts, meaningless sparklines or unnecessary animation.
- No made-up review stars, prices, ratings, AI confidence percentages, demo records or operational totals.
- No fake button interactions, broken links, dead-end empty states, or prototype screens presented as complete.
- No broad dependency/library changes without proving why existing primitives cannot handle the job.

## 8. Design skills and tools

Existing project assets:
- \`.agents/skills/valora-product-design/SKILL.md\` (update/obey this project-specific skill).
- \`.agents/mcp.json\` contains Playwright, Chrome DevTools, shadcn and Context7 server declarations. Do not assume Codex automatically reads this file; inspect Codex's actual MCP configuration and document the required setup without breaking working configuration.
- The frontend has Playwright Test configured. Inspect package scripts and E2E coverage before adding overlapping tools.

Evaluate this production UI skill for Codex:
- **Frontend Design Pro**: \`https://github.com/PGraeff/frontend-design-pro-agent-skill\`
- It is designed around product-specific creative direction, searchable design guidance and a UI-copy filter. Review its \`SKILL.md\` and license before installation or use; external skills are untrusted instructions until reviewed.
- If compatible and approved by the environment, the current published install command is:
  \`npx skills add PGraeff/frontend-design-pro-agent-skill --skill frontend-design-pro --global --agent codex --yes --copy\`
- Do not install several overlapping design packs just because they exist. Compare with Addy Osmani's \`frontend-ui-engineering\` skill (\`https://github.com/addyosmani/agent-skills/tree/main/skills/frontend-ui-engineering\`) only if a specific gap remains—especially component engineering, responsive behaviour or accessibility.
- The external skill supplements this brief; it never overrides VALORA's domain rules, tone, API constraints or anti-patterns.

Tool trade-offs:
| Tool | Use | Decision |
|---|---|---|
| Existing Playwright Test | Repeatable route, workflow, responsive and accessibility assertions | Keep and strengthen first |
| Playwright MCP | Agent-driven exploratory interaction in a live browser | Use if Codex supports it and it adds value beyond test automation |
| Chrome DevTools MCP | Inspect console, network, layout and runtime behaviour | Useful for diagnosis; verify Codex connection instead of assuming Freebuff's config applies |
| External design skill | Stronger creative direction and anti-generic UI review | Review and install at most one complementary skill; avoid overlapping instruction packs |
| Existing Tailwind/UI primitives | Shared accessible controls and tokens | Reuse where they help; don't force every layout into the same surface |

## 9. Browser and quality gates

Testing the component alone is insufficient. A route, link, role guard and nested shell must be verified through the app router.

For each major phase:
- Add/repair route-level tests and user-journey tests.
- Update stale tests when the product's intentional copy/UX changes.
- Ensure browser tests assert the target heading/content and key controls, not only that a page has no overflow.
- Run \`npm test\`, \`npm run build\`, and \`npm run test:e2e\` from \`frontend/\` when supported by the environment. If Chromium is not installed, use the documented Playwright installation path and accurately report whether tests ran.
- Inspect at minimum desktop (1440px wide) and mobile (390px wide); include tablet where layouts change materially.
- Capture screenshots of the homepage, directory, profile, admin overview, resident overview, provider work and AI response. Compare them visually before/after; verify one of each role under representative API data.
- Inspect browser console/page errors and important network failures. Confirm there is no sideways page overflow.
- Test loading, empty, error, insufficient-data and populated states.
- Test keyboard operation, focus management, semantic structure, contrast, reduced motion, and AI output formatting.
- Check \`git diff --check\`; keep API types, domain computations and authorisation responsibilities intact.

Do not claim browser verification if no browser was run. Use mocked data for deterministic visual tests when necessary, but do not treat a mocked screenshot as proof that production data or backend integration is correct.

## 10. Delivery sequence and completion definition

Execute one coherent phase at a time:

**Phase 0 — correctness and evidence**
- Verify current defects.
- Wire the public directory/profile routes.
- Correct role-based dashboard routing/actions.
- Fix misleading/stale E2E assertions so broken routes fail tests.
- Trace demo/public flags and correct sample/live classification safely with tests.
- Avoid stylistic changes in this phase unless required by correctness.

**Phase 1 — public discovery and editorial story**
- Establish hero copy/composition and image direction.
- Show published complexes near the top, with catalogue and detail journey.
- Preserve selected complex through access/signup.
- Verify route navigation and all public states.

**Phase 2 — dashboards and workspace hierarchy**
- Implement distinct administrator, resident and provider overviews.
- Reduce repeated cards and duplicated score detail.
- Tighten Intelligence hierarchy and the existing operational record screens.
- Inventory disconnected/prototype/sample-only routes and ensure no unfinished capability is falsely exposed.

**Phase 3 — AI conversation presentation**
- Implement the shared safe renderer and structured message layout.
- Add contextual follow-up chips and reliable conversation input states.
- Ensure evidence/source details and role-safe boundaries are respected.
- Test raw Markdown, plain text, headings, lists, links, tables, malformed output, long answers, empty/error responses and follow-up actions.

**Phase 4 — visual consistency and acceptance**
- Reconcile design tokens and shared UI primitives with the chosen visual direction.
- Refine responsive layout/accessibility and fix residual inconsistencies.
- Run all quality gates and inspect screenshots across all key roles.

A phase is complete only when its code, tests, visual verification and progress report agree. A successful build alone is not completion. Preserve working functionality and report honestly what remains.

## 11. Completion report format

At the end of each phase, report:

1. What changed and which user journey it improves.
2. Files changed and notable design decisions.
3. Automated checks run and exact results.
4. Browser sizes/routes/screenshots actually verified.
5. Known defects, assumptions and anything written but not run.
6. Next phase and any genuine blocker.

Do not ask the product owner to restate requirements already written here. Make defensible design decisions, state uncertainty, and keep moving.
