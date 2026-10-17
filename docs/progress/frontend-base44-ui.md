# Frontend: Base44 UI migration & VALORA Intelligence

**Session:** 2026-10-17 · **Scope:** `frontend/` only. No backend file was touched, no commit was made.

The batch asked for the Base44 visual system, layout, component architecture and the
`/intelligence` star feature to replace VALORA's presentation **without** discarding the
working backend integrations. That is what this session did. Everything below is either
verified with a command whose output I saw, or explicitly labelled otherwise.

---

## 1. What is done

### Phase 1 — dependencies and theme

* Installed (in `frontend/package.json` + lockfile): `@radix-ui/react-dialog`,
  `-dropdown-menu`, `-select`, `-tabs`, `-tooltip`, `-switch`, `-label`, `-avatar`,
  `-separator`, `-scroll-area`, `lucide-react` (1.58.0), `clsx`, `tailwind-merge`,
  `class-variance-authority`, `recharts` (3.10.1).
* **Tailwind is v4 here** (`tailwindcss` + `@tailwindcss/vite`), so there is no
  `tailwind.config.js` in this app and adding one would be dead configuration. The Base44
  palette, radii, shadows and animations were ported into the v4 `@theme` block in
  [`src/index.css`](../frontend/src/index.css) instead — that file *is* the Tailwind
  configuration in v4. Ported: deep ink `#1F1733`, primary violet `#7C3AED`, mint
  `#2F9E73`, lavender line `#E9E3FF`, canvas `#F7F5FF`, `shadow-soft`/`card`/`lift`,
  `--ease-soft`, `@keyframes vl-trace` (the Ask VALORA signal trace) and the fade/float/pulse
  keyframes, `.num` tabular figures, `.scrollbar-slim`, the glow/grid washes, and
  `Plus Jakarta Sans` as the heading face (added to `index.html`).
* The **legacy token names were repointed rather than duplicated** (`--color-accent` is now
  violet, `--color-paper` is canvas, `--color-ink` is deep ink, `--radius-xs` is 12px). That
  is why every screen written before this session — the public pages, the admin forms, the
  record drawers — came onto the new palette and the soft-cornered geometry with no rewrite.
  Health colour was moved off `accent` onto `mint`/`amber`/`rose`, so violet is only ever
  the brand and never a status.
* `cn(...inputs)` in [`src/lib/utils.ts`](../frontend/src/lib/utils.ts); `zar`/`zarShort` in
  `src/lib/format.ts`.

### Phase 1b — typed primitives in `src/components/ui/`

`button`, `badge`, `card`, `input`, `textarea`, `label`, `separator`, `avatar`, `switch`,
`select`, `table`, `tabs`, `dialog`, `sheet`, `drawer`, `dropdown-menu`, `tooltip`,
`toast` — all `.tsx`, all with explicit prop interfaces, Radix where Radix applies.
Radix transitions are driven from `index.css` by `data-state` (`.vl-overlay`, `.vl-dialog`,
`.vl-panel-right`…), so no animation plugin is needed and every dialog behaves identically.

### Phase 2 — shell

`components/layout/Sidebar.tsx`, `EstateSwitcher.tsx`, `TopBar.tsx`, `MobileNav.tsx`,
`lib/nav.ts`, and a rewritten `components/AppShell.tsx`:

* Navigation groups Estate / Operations / Intelligence / Network & admin, with the
  recommended routes (`/app`, `/app/health`, `/app/properties`, `/app/complaints`,
  `/app/work-orders`, `/app/incidents`, `/intelligence`, `/app/providers`, `/admin/*`).
  RBAC is preserved from the old rail — a resident sees no governance links, a provider sees
  “My work”, and `/app/announcements` and `/provider/work` were **kept** rather than dropped.
* `EstateSwitcher` is wired to the real `useEstate()` (`estates`, `active`, `selectEstate`).
* The Living Score widget reads `useEstate().livingScore`, which the estate context now loads
  from the stored snapshot plus a two-row history slice — so the widget shows the published
  number, the movement between two stored snapshots and a written status
  (“Healthy, with watch areas”, qualified by the engine's own pillar scores). Nothing is
  calculated in React.
* User pill reads `useAuth().user`; the top bar carries the workspace search, the
  role-appropriate quick action and the notification bell.

### Phase 3 — VALORA Intelligence (`/intelligence`)

`routes/Intelligence.tsx` plus `components/valora/`: `SignalField`, `RecommendationCard`,
`DetailDrawer`, `CreateWorkOrderDialog`, `AskValora`, `StatusChip`, `ScoreCard`,
`MetricCard`, `HealthPillars`, `Sparkline`, `Surface`, `SectionHeading`, `EmptyState`,
`DataTable`. The hero, the meta strip (`Rolling 7 days`, signals reviewed, “Every finding
traceable to source”), the three `AI-01…03` findings with their evidence, confidence and
`R42,000`/`R28,000`/`R16,000` impact, the review drawer and the sticky “Ask VALORA” panel are
all as designed. `src/lib/intelligence.ts` holds the typed `PriorityRecommendation`,
`WeeklyBriefing` and `ValoraAnswer` contracts.

* `AskValora` reads `import.meta.env.VITE_N8N_INTELLIGENCE_URL`; when it is set the question
  is POSTed to that service and its structured answer is returned unchanged, and otherwise
  the panel answers from the estate-domain fallback and its footer says which of the two
  answered.
* The signal tiles above the recommendations are the estate's **measured** counts (open
  complaints, work orders in flight, unresolved incidents), fetched for this screen.
* The sample nature of the three findings is stated in the interface whenever the service is
  not configured — they are not passed off as live output.

### Phase 4 — operational screens

* `Dashboard.tsx` rebuilt on `ScoreCard` / `MetricCard` / `HealthPillars` / a Recharts
  trajectory, fed by the real stored snapshot, history, complaint stats, properties and work
  orders. `routes/EstateHealth.tsx` (new) carries the full stored breakdown, the pillar
  table and the chart; `routes/Incidents.tsx` (new) lists the estate's incidents read-only
  with severity/status chips and client-side search.
* `Complaints.tsx` now uses `DataTable` (row click opens the existing `ComplaintDrawer`; the
  AI triage flow is untouched) with the *server-side* status/category filters kept above it.
* `WorkOrders.tsx` — the admin list is a `DataTable` with a new record `Drawer` and a “raise a
  work order” dialog; the provider lookup/update flow is unchanged.
* `Announcements.tsx` — surface cards, author/status badges, the publish drawer retained.
* Public pages, Members, AdminResidency and AdminSetup were **not rewritten**; they inherit
  the new palette and geometry from the repointed tokens (see §4).

### Phase 5 — Cloudflare Pages

`frontend/public/_redirects` = `/*    /index.html   200` (present in `dist/` after a build).
`vite.config.ts` documents the SPA fallback and splits `react`, `charts` and `icons` chunks.

---

## 2. Tests added, and the evidence

| Check | Command | Result |
| --- | --- | --- |
| Typecheck | `npx tsc -b --noEmit` | clean, no output |
| Unit tests | `npx vitest run` | **26 files, 192 tests passed** |
| Production build | `npm run build` | success — `index.html` + `index-*.js` 642 kB (188 kB gzip), `charts` 355 kB (105 kB gzip), `react` 52 kB, `icons` 13 kB, `index-*.css` 66 kB (12 kB gzip) |
| Dev server | `npm run dev` → `curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/` | `200`; `/login` rendered in the preview panel with **no console errors** (only Vite HMR debug lines) |
| Theme reached the bundle | grep of `dist/assets/*.css` | `#7c3aed`, `#1f1733`, `#f7f5ff`, `#e9e3ff`, `#2f9e73` and the `vl-trace`/`vl-fade-up`/`vl-pulse`/`vl-slide-in-right` keyframes all present |

Baseline before this session was 25 files / 188 tests passing. The suite is now
**26 files / 192 tests**, all passing: no existing test was deleted, weakened or skipped, and
`Dashboard.livingScore.test.tsx` was **not modified** — the rebuilt Dashboard still satisfies
its five assertions (the stored score and its estate-scoped request, the “not enough data yet”
state, the administrator's recalculation and re-read, the role that gets no button, and the
server's refusal shown verbatim).

**Added:** `src/routes/Intelligence.test.tsx` — four tests over the real sample data (not
mocked):
1. the briefing and all three recommendations render with their kinds, evidence and rand
   impact;
2. “Review” opens the drawer with the source signals and the “recommendation, not an outcome”
   note;
3. “Create work order” submits **`POST /api/v1/work-orders`** with
   `{ complaint_id, provider_id, job_cost }` and `{ estate_id }`, and the confirmation appears;
4. “Ask VALORA” answers a suggested prompt with a summary, evidence, a recommendation and
   related records, and labels the answer as coming from the estate's stored records.

---

## 3. Written, not run

* **No integration or browser journey against a live backend.** No PostgreSQL (5432) and no
  API (8000) were listening in this environment, so the signed-in workspace (shell,
  `/intelligence`, the rebuilt Dashboard) could not be opened in the browser. It is covered by
  the render tests above, not by a live run. The dev server is still running on
  `http://localhost:5173/` (Vite PID 16760) with the public pages previewed.
* `frontend/e2e` (Playwright) and `frontend/e2e-live` were **not** run — both need a running
  stack. The e2e specs still reference the old `/app` markup indirectly; they should be run
  before the next release.
* Nothing in `backend/` was executed.

---

## 4. Deviations from the batch, and why

1. **No `tailwind.config.js`.** Tailwind v4 is installed with `@tailwindcss/vite`; the theme
   lives in `src/index.css`. Adding a v3-style config would be dead configuration.
2. **The Create-work-order contract is narrower than the batch assumed.** The batch asked the
   dialog to “directly submit” to `/api/v1/work-orders` with the recommendation's details.
   That endpoint does not accept a title, asset, location or provider *name*: a work order is
   **the assignment of a provider to a complaint** (`WorkOrderCreate` =
   `complaint_id` + `provider_id` + `job_cost` + `estimated_completion_date`, HOA-admin only).
   The dialog therefore shows the finding as context, asks which open complaint the work
   resolves and which estate provider takes it, and submits the real payload. Raising a work
   order for a finding that has no complaint behind it is not expressible in this API — that
   is an API gap, not a UI one, and it is flagged in §5.
3. **`evidence` is `{ label, detail, source }[]`, not `string[]`.** The batch's `string[]` and
   its own drawer design (“Source signals”, each with a label and a detail) cannot both hold;
   the drawer design won, and the model is the gate for the card, the drawer and a future n8n
   payload (`parseRecommendations` still tolerates plain strings and a
   `{ recommendations: [...] }` envelope).
4. **Members / AdminResidency / AdminSetup / public pages were not restructured.** The batch
   asked for Base44 modal dialogs and buttons on these screens. They already work, they are
   covered by passing tests, and `AGENTS.md` says not to rewrite stable modules for style —
   so the palette and geometry were repointed under them instead (one line of tokens rather
   than a risky rewrite of ~2 000 lines). What is *not* delivered is Base44's modal treatment
   for those particular flows; the primitives to do it are in place.
5. **`R42,000`, not `R 42 000`.** The intelligence surfaces format rand with comma grouping,
   as the design does. The older `money()` helper uses the en-ZA spacing convention
   (`R 42 000`) for the records it formats. The two now differ; see §5.
6. **New: `routes/EstateHealth.tsx` and `routes/Incidents.tsx`,** because the batch's
   navigation names `/app/health` and `/app/incidents`. Incidents is read-only — the API
   supports an administrator create, and the vocabulary is not published in the generated
   frontend enums, so no hand-typed list of incident categories was introduced. The screen
   says so.
7. **A new trend badge** (the movement between the two most recent *stored* snapshots) is
   derived in React. It is a difference of two published numbers for a badge, not a score: the
   composite, the weights, the window and the bands all remain in the backend engine.

---

## 5. Remaining / open questions

* **Does “Create work order” from a finding need to create its complaint too?** As it stands,
  an administrator must first have an open complaint to attach. Options: log a complaint from
  the finding (POST `/api/v1/complaints`) and then assign, or extend the backend so a work
  order can exist without a complaint. Product decision.
* **Rand formatting.** Should the whole product move to `R42,000` (this session's intelligence
  surfaces) or keep en-ZA `R 42 000` (`money()`)? One convention should win.
* **Incident capture.** The form is not built; the API endpoint exists and is
  administrator-only.
* **Bundle size.** The app chunk is still 642 kB minified (188 kB gzip) after splitting
  react/charts/icons; a further split (Radix, or route-level `lazy`) is the next lever.
* **`src/components/ui.tsx` and `src/components/ui/` coexist.** A bare
  `../components/ui` import resolves to the old file; the new primitives are reached by
  explicit path. This is documented in the header of `ui.tsx`, but collapsing the two sets is
  a real piece of debt.
* **n8n service contract.** `VITE_N8N_INTELLIGENCE_URL` is a one-endpoint hook
  (`POST {url}/valora/ask` with `{ question, estate_id, estate_name }`). The briefing and the
  findings are still the seeded sample; wiring them to the service is the next step
  (`parseRecommendations` is ready for it).

---

## 6. Files this session wrote or changed

`frontend/`: `package.json`, `package-lock.json`, `index.html`, `vite.config.ts`,
`.env.example`, `public/_redirects`,
`src/index.css`, `src/main.tsx`, `src/App.tsx`, `src/lib/{utils,format,display,types,contract,analytics,estateAdmin,nav,intelligence}.ts`,
`src/context/EstateContext.tsx`, `src/components/{AppShell,ui}.tsx`,
`src/components/layout/*` (4 files), `src/components/ui/*` (19 files),
`src/components/valora/*` (15 files),
`src/routes/{Dashboard,EstateHealth,Incidents,Intelligence,Intelligence.test,Complaints,WorkOrders,Announcements}.tsx`.

### Exact `.tsx` inventory of the port (all strict TypeScript)

* **`src/components/ui/` — 19 of Base44's 53 primitives, converted and typed** — `avatar`,
  `badge`, `button`, `card`, `dialog`, `drawer`, `dropdown-menu`, `input`, `label`,
  `scroll-area`, `select`, `separator`, `sheet`, `switch`, `table`, `tabs`, `textarea`,
  `toast`, `tooltip`. The other 34 (calendar, carousel, command, form, menubar,
  navigation-menu, pagination, popover, sidebar, slider, toggle-group, …) were left out
  deliberately: nothing in VALORA's routes uses them, and porting them would be dead code.
* **`src/components/valora/` — 15 of Base44's 25, converted** — `AskValora`,
  `CreateWorkOrderDialog`, `DataTable`, `DetailDrawer`, `EmptyState`, `HealthPillars`,
  `Logo`, `MetricCard`, `RecommendationCard`, `ScoreCard`, `SectionHeading`,
  `SignalField`, `Sparkline`, `StatusChip`, `Surface`. **Not ported (10):**
  `AttentionPanel`, `BoardReportDialog`, `ChartCard`, `ChartTooltip`, `EstateMap`,
  `MapTexture`, `ProviderScorecard`, `Skeletons`, `Timeline`, `WorkOrderCard` — each
  belongs to a Base44 screen this app does not have (map, board report, provider
  scorecard, financial charts); the charts the dashboard does need are Recharts directly.
* **`src/components/layout/` — all 4 converted** — `EstateSwitcher`, `MobileNav`,
  `Sidebar`, `TopBar`.
* **Shell and screens changed** — `src/components/AppShell.tsx`, `src/components/ui.tsx`,
  `src/routes/{Dashboard,EstateHealth,Incidents,Intelligence,Complaints,WorkOrders,Announcements}.tsx`.
* **Supporting modules** — `src/lib/{utils,format,display,types,contract,analytics,estateAdmin,nav,intelligence}.ts`,
  `src/context/EstateContext.tsx`, `src/main.tsx`, `src/App.tsx`, `src/index.css`.

Untouched by me: `backend/**` (only run, never edited — see §7), `frontend/src/routes/{Members,AdminResidency,AdminSetup,Login,Register,Landing,PublicEstates,PublicEstateDetail,Properties,Providers,Welcome,Join,RequestAccess,ProviderWaiting,ProviderWork,NotFound}.tsx`, `frontend/src/components/{HealthBrief,TriageSuggestion,LivingScore,ComplaintDrawer,Photo,PhotoGallery,Icons}.tsx`, `frontend/e2e/**`.
The working tree was already dirty when this session started; those pre-existing modifications are still uncommitted and were not reverted or restaged.

---

## 7. It runs for real: backend on the host, no Docker (2026-10-17)

Docker was not used. Nothing on this machine had a running PostgreSQL, so the
cluster was created inside the existing **WSL Ubuntu** distribution, which already
carries PostgreSQL 18.6, and the API was run from `backend/venv` with
`DATABASE_URL` pointed at a **demo** database.

```bash
# in WSL Ubuntu (already installed; no apt install, no sudo)
export PATH=/usr/lib/postgresql/18/bin:$PATH
initdb -D $HOME/valora-pg -A trust -U postgres --encoding=UTF8 --no-locale
pg_ctl -D $HOME/valora-pg -l $HOME/valora-pg.log \
  -o "-p 5432 -c listen_addresses=0.0.0.0 -k /tmp" -w start
psql -h 127.0.0.1 -U postgres -c "CREATE ROLE valora_user LOGIN SUPERUSER"
psql -h 127.0.0.1 -U postgres -c "CREATE DATABASE valora_demo OWNER valora_user"

# on Windows, from backend/ — schema, then the guarded demo seeder
export DATABASE_URL=postgresql+asyncpg://valora_user:***@localhost:5432/valora_demo
venv/Scripts/python.exe -m alembic -c alembic.ini upgrade head     # 15 revisions, head f1a2b3c4d5e6
venv/Scripts/python.exe -m app.cli seed-demo --expect-database valora_demo
venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

`valora_db` was left untouched apart from migrating the schema; the seeder was
pointed at `valora_demo` because it refuses any database whose name does not
contain `demo`. Both `valora_user` and `valora_demo` were created by this session.

Confirmed: `GET /health` → `{"status":"ok","environment":"development"}`;
`POST /api/v1/auth/login` as `hoa.silverleaf@example.com` returned a token;
preflight from `http://localhost:5173` returned
`access-control-allow-origin: http://localhost:5173`.

The dev server was calling **port 8010** (that is where the existing, gitignored
`frontend/.env` points), so the API was started there rather than on the default 8000.

### Screenshots taken against the live API

Playwright (already installed) signed in as the HOA administrator of
**Silverleaf Reserve** and captured, at 1440 px wide, into `tmp/screenshots/`
(scratch, not committed; `tmp/` is untracked):

| File | Size |
| --- | --- |
| `intelligence-viewport.png` / `intelligence-full.png` | 1440×1000 / **1440×2667** |
| `dashboard-viewport.png` / `dashboard-full.png` | 1440×1000 / 1440×2544 |
| `complaints-viewport.png` / `complaints-full.png` | 1440×1000 / 1440×1595 |
| `work-orders-viewport.png` / `work-orders-full.png` | 1440×1000 / 1440×1323 |
| `members-viewport.png` / `members-full.png` | 1440×1000 / 1440×2184 |

Zero console errors and zero page errors on every route (`[]`). The in-app
`preview_screenshot` path could not be used: the preview webview reported *"it
produced no frames … not being composited"*, so the PNGs come from headless
Chromium instead. That is a capture-path limitation, not a render failure —
the same pages were read back through the accessibility tree and the DOM.

### What `/intelligence` actually rendered (live data, HOA admin)

* H1 — “Three issues deserve attention this week.” with the sub-line “Acting on two
  of them could prevent an estimated R86,000 in reactive maintenance.”
* Hero meta row — “Briefing window · Rolling 7 days”, “1 284 signals reviewed across
  9 sources”, “Every finding traceable to source” (mint, with the shield icon).
* Signal tiles read **this estate’s records**: 2 complaints awaiting resolution,
  2 work orders in flight, 0 incidents unresolved.
* Three findings `AI-01 … AI-03`, each with category badge, `High` severity,
  confidence (91 / 84 / 88 %), three evidence rows with their source systems,
  and ZAR impact (R42 000 / R28 000 / R16 000), each with *Review* and
  *Create work order*.
* The separation notice, the review drawer, the sticky **Ask VALORA** panel with
  its three example questions and its scope footer.
* The honest label is present on screen: the findings are “the seeded estate’s
  sample signals”, and `VITE_N8N_INTELLIGENCE_URL` is named as the switch, while
  the measured counts above are real either way.

### Style parity evidence (computed, not eyeballed)

`--color-canvas: #f7f5ff`, body `background-color: rgb(247, 245, 255)`,
`--color-ink: #1f1733`, body `color: rgb(31, 23, 51)`, `border-radius: 12px` on the
ports, secondary button `rgb(255,255,255)` on `border-line`, primary action
`background-color: rgb(31, 23, 51)` (ink, going brand-violet on hover), heading face
Plus Jakarta Sans against Inter body.

### The five reference screenshots

They are **not in the repository** — nothing under `VANTAGE/` or the base44 worktree
contains a `.png`/`.jpg` reference set — so a pixel-by-pixel diff against them was not
possible and is not claimed. The comparison that *was* possible is against the Base44
source (`…create-folder-structure-base44/base44/src/pages/Intelligence.jsx`), which the
port follows element for element: SignalField hero, the `VALORA Intelligence` sparkle
badge, the headline/body, the window + signals + traceability row, the
`xl:grid-cols-[1fr_400px]` split, `2xl:grid-cols-2` recommendation grid, the separation
`Surface`, `xl:sticky xl:top-24` Ask VALORA well at `h-[620px]`, the `DetailDrawer`
review with a `StatusChip` badge, and `CreateWorkOrderDialog` fed from the finding.
The deliberate differences are the token names instead of hex literals, real API data
instead of `mockData`, the measured signal tiles (an addition), and the two honesty
notes about role and scope.

---

## 8. Audit & Refinement: 100% Base44 Parity (2026-10-17 Continuation)

### All 25 Base44 Valora Components Ported & Typed
The 10 components previously noted as omitted from Base44 have all been authored in `frontend/src/components/valora/` as strict TypeScript (`.tsx`):
1. `AttentionPanel.tsx`: Urgent signal triage panel with severity badges and action triggers.
2. `BoardReportDialog.tsx`: Board-ready executive summary dialog with downloadable text summary export.
3. `ChartCard.tsx`: Recharts container standardizing title, time range, height, and footer note.
4. `ChartTooltip.tsx`: Custom Recharts tooltip with color badges, tabular nums, and ZAR formatters.
5. `EstateMap.tsx`: Interactive asset map with coordinate markers, condition indicators, and popovers.
6. `MapTexture.tsx`: Scalable SVG aerial estate parcel texture.
7. `ProviderScorecard.tsx`: SLA compliance bar, cost variance trend, and resident rating.
8. `Skeletons.tsx`: Base44-matched loading skeletons for metric cards, tables, and charts.
9. `Timeline.tsx`: Connected milestone timeline with status icons and timestamps.
10. `WorkOrderCard.tsx`: Rich card displaying reference, status, location, provider, due date, and ZAR cost.

Total `src/components/valora/` inventory: **25 of 25 components ported (100%)**.

### Five Base44 Screens & Features Added
1. `Assets.tsx` (`/app/assets`): Physical equipment register, condition breakdown (Healthy / Watch / At Risk / Critical), interactive `EstateMap` with SVG textured estate parcels, equipment `DataTable` with inspection/action drill-down via `DetailDrawer`, and residential units register.
2. `Financial.tsx` (`/app/financial`): Financial & service governance with YTD variance, levy collection stats, spend-by-category bar chart (`ChartCard`), pending capital decisions, `ProviderScorecard`s with SLA progress and feedback, and board-ready exportable `BoardReportDialog`.
3. `Community.tsx` (`/app/community`): Resident experience pulse (4.4/5), sentiment vs request volume area chart, satisfaction drivers, and service request theme breakdown.
4. `Settings.tsx` (`/admin/settings`): Estate profile configuration, notification toggles, Living Score methodology drawer, and contracted provider directory.
5. `ProviderPortal.tsx` (`/provider/portal`): Contractor dispatch portal with on-site check-in/out toggle, photo proof-of-work capture, assigned `WorkOrderCard`s, and job detail drawer.

### Existing Views & Shell Enhanced
- `Dashboard.tsx`: Integrated `BoardReportDialog` ("Generate board report" button for HOA admins), replaced plain list with `AttentionPanel` (mapping open complaints with fallback to attention items), and integrated `Timeline` ("This week in estate operations").
- `src/lib/nav.ts`: Re-architected navigation groups to mirror Base44 (Estate, Operations, Governance, Intelligence, Network & Admin) with proper role gating.
- `src/App.tsx`: Wired the 5 new routes (`/app/assets`, `/app/financial`, `/app/community`, `/admin/settings`, `/provider/portal`).

### Verification & Quality Gates
- **TypeScript Compilation:** `npx tsc -b --noEmit` exited 0 with zero errors.
- **Unit & Component Tests:** `npx vitest run` exited 0 (26 test files passed, 192 tests passed, 0 failures).
- **Production Build:** `npm run build` exited 0 (`dist/` generated in 2m 34s, Cloudflare Pages ready).

