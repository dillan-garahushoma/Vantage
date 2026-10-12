# BATCH AI-5 — Frontend AI surfaces (Health Brief and triage suggestions)

Session: 2026-10-11. Branch `valora-work`. **No backend file was touched, no migration was edited,
nothing was committed.** All work is in `frontend/` (untracked as a whole: `?? frontend/`) plus this
note.

## The previous stop is cleared

An earlier session wrote this file as a STOP: the triage override dropdowns could not get their
allowed values from the contract, and the batch forbids hardcoding them or adding an endpoint. That
gate has since been closed by the backend/contract work, so this batch ran:

```text
TriageDecisionRequest.category  -> enum [water, electrical, security, noise, infrastructure,
                                        gardens, waste, parking, administrative, other]
TriageDecisionRequest.priority  -> enum [low, normal, high, urgent]
TriageDecisionRequest.trade     -> enum [plumber, electrician, security, landscaping,
                                        general_maintenance, pest_control, roofing, other]
```

Evidence: `docs/openapi.json` (`components.schemas.TriageDecisionRequest`) and the generated
`frontend/src/api/generated/enums.ts` (`triageCategories`, `triagePriorities`, `triageTrades`,
`triageDecisions`). The panel imports those, and a test asserts the dropdown options equal them
exactly. `npm run check:api` → exit 0.

## Delivered

| File | What it is |
| --- | --- |
| `frontend/src/lib/ai.ts` | Typed calls for both features on the existing client/session/error envelope: `readHealthBrief`, `generateHealthBrief`, `sendHealthBriefFeedback`, `readTriageSuggestion`, `requestTriageSuggestion`, `decideTriageSuggestion`, `isAiUnavailable`. Types come from `src/api/generated/schema.d.ts`; nothing is retyped. |
| `frontend/src/components/HealthBrief.tsx` | The brief: headline/summary/drivers/actions, source wording, demo badge, `as_of`, "Show the figures" table (facts verbatim), generate button (admins), Helpful/Not helpful with a 500-char counter. |
| `frontend/src/components/TriageSuggestion.tsx` | Advisory review: suggest, accept, override (generated enum dropdowns, at least one change), dismiss, read-only afterwards with who/when/what, provider trade link, anonymous/503/403/404 copy. |
| `frontend/src/routes/Dashboard.tsx` | `<HealthBrief>` on the dashboard for admins **and** residents (the dashboard is the resident estate view); admin-only generate. |
| `frontend/src/components/ComplaintDrawer.tsx` | `<TriageSuggestion>` in the complaint detail, rendered only when `isAdmin`. |
| `frontend/src/routes/Providers.tsx` | Reads `?trade=` so the triage trade link lands pre-filtered. |
| `frontend/src/components/ui.tsx` | `Select` typed as `ComponentPropsWithRef<'select'>` so a revealed form can take focus (React 19 ref-as-prop). |
| `frontend/src/components/aiSurfaces.guard.test.ts` | Source-level guards: no scoring/engine/inference imports, enum vocabulary only from the generated file, and no contract vocabulary retyped as a string literal. |
| `frontend/e2e-live/*`, `frontend/playwright.live.config.ts` | The live wiring check (see below), kept out of `e2e/**` so the default smoke run never needs an API. |

Presentation only, as required: no score, delta, weight or category is computed in the client. The
figures table prints exactly what the API returns, and a test pins an internally inconsistent pair of
deltas (`delta_30d = +1.5`, `delta_30d_abs = 9.9`) to prove the client does not reconcile them.

## Tests — 7 files / 52 tests, all passing

`npm test` (Vitest + RTL + jsdom), exit 0:

```text
Test Files  7 passed (7)
     Tests  52 passed (52)
```

New in this batch:

- `HealthBrief.test.tsx` (18): AI wording vs "Automatic summary" with no AI wording; demo badge only
  for `data_origin=demo`; `as_of` always shown; quiet "Showing the automatic summary." for
  `ai_unavailable_reason` with no error and no reason code in the DOM; drivers/actions rendered;
  facts table verbatim incl. the inconsistent delta; expander collapse; generate visible only for
  admins, disabled while pending, no double submit, panel updated in place with no second read;
  request id shown on an unexpected failure; a rejected generate request (422) reported with its
  reference and the existing brief left on screen; feedback only for `source=ai`; 500-char counter and form
  reset; 409 → "Already submitted"; loading/404-as-empty/403/network-retry states; keyboard and focus
  order with the expander toggled by Enter and Space.
- `TriageSuggestion.test.tsx` (18): advisory copy that promises no automatic or emergency action;
  anonymous 409 copy without retry; **a resident never renders the panel or calls the endpoints**;
  suggest → labels + `provider · model · prompt_version`; trade link
  `/app/providers?trade=plumber`; accept → read-only "Accepted" with who/when; dismiss → "no labels";
  override dropdown options equal the generated enums; override requires a change (including
  changing back); override shown in the read-only view; 503 → "Suggestions are not available right
  now." with no reason code; 409 → already decided and reloaded; 403; 404; network retry; stored
  decision on open; keyboard and focus order (the revealed form takes focus, disabled Save is out of
  the tab order).
- `aiSurfaces.guard.test.ts` (5): the "presentation only" guards above.

Flake fixed at the cause, not by weakening assertions: the facts test was timing out at Vitest's 5 s
default because each file built a fresh jsdom while the whole suite ran in parallel.
`vitest.config.ts` now uses `pool: 'vmThreads'` (one jsdom per worker, per-file isolation kept) and a
15 s per-test budget. Assertions are unchanged; the suite went from ~43 s to ~30 s.

## Verification (exact commands and results)

```text
frontend> npm test          -> 7 files / 52 tests passed, exit 0
frontend> npm run typecheck -> tsc -b --noEmit, exit 0
frontend> npm run build     -> tsc -b && vite build, exit 0
                              dist/assets/index-*.js 384.59 kB (gzip 113.81 kB), css 33.93 kB (6.82 kB)
frontend> npm run check:api -> "the generated API files match docs/openapi.json", exit 0
```

**Lint: not run — this repository has no linter** (no eslint/biome/prettier config, no `lint`
script in `frontend/package.json`), and FE-1's dependency rule (no new dependency without a
justification and a 14-day-old release) rules out adding one in this batch. Reported as unavailable,
not as a pass.

**Backend suite: untouched and not rerun.** I made no backend change of any kind; the backend
modifications visible in `git status` predate this session and belong to earlier batches.

## Browser wiring check (Playwright against the real backend) — ran, both ways

Environment (all windows-local, throwaway): a fresh database `valora_ai5_wiring` migrated with
`alembic upgrade head`, seeded with `python -m app.cli seed-demo`, then given extra complaint /
work-order / incident history so the deterministic engine returns a measured score
(`recalc-living-scores --include-demo` → `status=scored score=54.59`). The API ran on
`127.0.0.1:8015` with `ENVIRONMENT=development`, `AI_PROVIDER=fake`, `AI_MODEL=fake-deterministic`,
`AI_INSIGHTS_ENABLED=true`, `AI_TRIAGE_ENABLED=true`, `AI_PERSONAL_DATA_ALLOWED=true`; the client ran
on `localhost:5199` with `VITE_API_BASE_URL=http://127.0.0.1:8015` (its `CORS_ORIGINS` included that
origin). Commands: `npm run test:e2e:live` with `E2E_BASE_URL=http://localhost:5199`.

```text
AI on  (e2e-live/ai-on.spec.ts)   4 passed (1.6m)
  ok  an HOA admin generates the brief, expands the figures and rates it
  ok  an HOA admin requests triage for a complaint and accepts it
  ok  a resident sees the brief and no triage review anywhere
  ok  both panels stay usable at a mobile width without horizontal overflow
AI off (e2e-live/ai-off.spec.ts)  3 passed (1.6m)
  ok  the brief falls back to the automatic summary with no AI wording and no error
  ok  the triage panel says suggestions are unavailable, without a reason code
  ok  a resident can still read the estate without the AI layer
```

**This is a WIRING result, not a model-quality or real-provider result.** The provider was the
deterministic fake, so the runs prove the client calls the real endpoints with the real shapes and
renders what comes back; they say nothing about Gemini.

What the AI-on run observed on screen: `source=ai` wording after generate, the demo-data badge, the
facts table, `POST .../feedback` accepted; the triage panel's suggested labels with
`fake · fake-deterministic · triage-v1`, a decision posted and the panel turning read-only; a
resident seeing the brief and no triage UI; no console errors, no uncaught page errors, no 5xx in the
watched windows.

Preconditions worth recording, because they are what makes those paths work:

- `AI_TRIAGE_ENABLED` and `AI_INSIGHTS_ENABLED` are per-feature flags (default **false**); with
  `AI_TRIAGE_ENABLED` unset the triage POST answers 503 and the panel shows the quiet unavailable
  message — which is what my first two attempts hit.
- `AI_PERSONAL_DATA_ALLOWED` must be on for triage: it sends resident-written text, which the guarded
  client classes as personal data and refuses by default.
- The AI-off fallback is only observable on an estate with **no stored AI artifact**: with a stored
  insight the read returns `source=ai` (correctly — the brief really was written by AI), and a stored
  suggestion is write-once. My first AI-off attempt failed for exactly this reason; after deleting
  `ai_insights` and `complaint_ai_suggestions` rows in the throwaway database, all three passed.

Observations, reported rather than hidden:

- A `GET /api/v1/properties?...` returned 500 once in the server log. The traceback is an
  `asyncio.CancelledError` while acquiring a database connection — the page was closing with the
  request in flight. Dev-environment noise, not a code defect, and unrelated to this batch.
- At 390 px the *dashboard as a whole* overflows by 275 px, from blocks outside this batch (the
  pages' other tables are not wrapped in scroll containers). My panels stay inside the viewport: the
  figures table scrolls in its own box, which the mobile test asserts and annotates.

## Deviations from the batch text

1. **axe-style accessibility check: not run.** The project has no a11y test dependency, and the
   dependency rule blocks adding one in this batch. The batch allows this ("if the project has one").
   Keyboard reachability and focus order are covered by tests instead.
2. `vitest.config.ts` gained `testTimeout: 15_000` and `pool: 'vmThreads'` — the fix for the flake
   described above.
3. `frontend/package.json` gained one script, `test:e2e:live`; `playwright.live.config.ts` and
   `e2e-live/**` are new and deliberately excluded from the default `playwright.config.ts` run.
   `tsconfig.node.json` includes them and now carries `DOM` in `lib` (they are browser specs).
4. The AI-on spec tolerates two states that a stateful database makes unavoidable, and says so in
   comments: feedback may answer 409 "Already submitted" (write-once by design) and the triage panel
   may already be decided. The fresh paths are the ones asserted in detail.

## Remaining / open questions

- A repeat of the AI-off run needs a database with no `ai_insights` rows, and a repeat of the fresh
  triage path needs `complaint_ai_suggestions` cleared. Worth a small reseed helper if this check is
  to run in CI.
- The 275 px dashboard overflow at mobile width is real and unfixed (outside this batch).
- No linter exists, so the "lint" gate in the batch remains unsatisfiable in this repository until
  someone decides to add one.
- The owner still has to run the real-provider (Gemini) check by hand.
