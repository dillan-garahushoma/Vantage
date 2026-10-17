# BATCH FE-1 — Generated API types, test tooling, and the drifted lists

Session: 2026-10-11. Branch `valora-work`. Status: **done**. No backend file was touched, nothing was
committed or reset, and no browser binaries were downloaded.

## Gate: BE-1 is in place

`docs/openapi.json` publishes the vocabularies, so this batch could proceed. Read straight out of the
contract before any edit:

```
ComplaintCreate.category            enum [water, electrical, security, noise, infrastructure, gardens, waste, parking, administrative, other]
ComplaintCreate.priority            enum [low, normal, high, urgent]
TriageDecisionRequest.category      anyOf[enum[10 categories], null]
TriageDecisionRequest.priority      anyOf[enum[4 priorities], null]
TriageDecisionRequest.trade         anyOf[enum[plumber, electrician, security, landscaping, general_maintenance, pest_control, roofing, other], null]
TriageDecisionRequest.decision      enum [accepted, overridden, dismissed]
TriageSuggestionResponse            suggested_* and decided_* enums present
```

See `docs/progress/be-1.md` for how they got there.

Skills read: `valora-architecture`, `valora-api-contracts`, `valora-quality-gates`,
`valora-product-design`. **Not present in the tree**: `frontend-app-builder` and `playwright-cli`
(the batch names them), and `valora-session-protocol`, `valora-testing`, `valora-security-review`,
`valora-migration-safety`, `valora-code-review` (AGENTS.md names those). `ls .agents/skills/` shows
seven directories — unchanged from AI-5's note; not fixed here.

## 1. Generated contract types and runtime vocabularies

New dev dependency **openapi-typescript 7.13.0** (exact), and:

| Script | What it does |
| --- | --- |
| `npm run gen:api` | `node scripts/gen-api.mjs` — writes `src/api/generated/schema.d.ts` + `enums.ts` from `docs/openapi.json` |
| `npm run check:api` | `node scripts/check-api.mjs` — regenerates into a scratch dir and fails (exit 1) if either committed file differs |

`src/api/generated/schema.d.ts` — 3,079 lines of types for the whole contract (openapi-typescript
7.13.0, 382 ms).

`src/api/generated/enums.ts` — the six vocabularies the UI needs as **runtime** arrays:
`complaintCategories`, `complaintPriorities`, `triageCategories`, `triagePriorities`, `triageTrades`,
`triageDecisions` (plus their `(typeof x)[number]` types). Every value is read out of the contract's
`enum` arrays; nothing is typed into the generator by hand. It fails loudly (non-zero exit, message
naming the field) if a field disappears, publishes no enum, repeats a value, or publishes something
that is not `[a-z][a-z0-9_]*`.

**Why `enums.ts` rather than openapi-typescript's own enum output.** The batch says to use the
generator's runtime-enum output if it has one. It has one — `--enum` ("Generate true TS enums rather
than string unions", documented at openapi-ts.dev/cli and openapi-ts.dev/advanced) — and it does
cover inline property enums, not just named schemas. But openapi-typescript writes **`.d.ts`**, and a
`.d.ts` has no runtime presence: the declarations would satisfy `tsc` while the value a dropdown
reads would not exist at run time. So `gen:api` keeps the types file as plain unions
(`schema.d.ts`, never imported at runtime) and derives `enums.ts` from the same published `enum`
arrays. That is the batch's "otherwise" branch, taken for a concrete reason rather than preference.

`check:api` compares bytes in a scratch directory (`os.tmpdir()`), not with `git diff`, because
`frontend/` is untracked in this working tree — `git diff` cannot see an untracked file, so a
git-based guard would have passed unconditionally.

## 2. Test tooling — pinned, and why these versions

Every package below is pinned exactly (`--save-exact`), and each released **on or before 2026-09-27**
(14 days before today, 2026-10-11). Versions were chosen from `npm view <pkg> time --json`.

| Package | Version | Published | Why |
| --- | --- | --- | --- |
| openapi-typescript | 7.13.0 | 2026-02-11 | Contract → types; newest release at all |
| vitest | 5.0.2 | 2026-09-25 | Runner. 5.0.3 (2026-09-30) rejected as too new |
| @testing-library/react | 16.3.3 | 2026-08-27 | Component rendering |
| @testing-library/user-event | 14.6.7 | 2026-09-02 | Real user interactions |
| @testing-library/jest-dom | 7.0.1 | 2026-08-09 | DOM assertions |
| jsdom | 29.1.1 | 2026-04-30 | DOM environment. 30.1.2 (2026-10-04) too new; 30.1.1/30.1.0/30.0.x declare `engines: ^22.22.2 \|\| ^24.15.0 \|\| >=26` and this machine runs Node **v24.14.1**, so they install with `EBADENGINE` — 29.1.1 accepts `>=24.0.0` |
| @playwright/test | 1.63.0 | 2026-09-04 | E2E runner. 1.64/1.65 were pre-release only |

One extra package arrived by itself: **@testing-library/dom 10.4.2**, a *required* peer of
@testing-library/react 16, auto-installed by npm. It is not in `package.json` (it is not a new
dependency choice, it is a peer of one of the named packages) but it is recorded in
`package-lock.json`.

New files: `vitest.config.ts` (jsdom, `setupFiles`, `src/**/*.test.{ts,tsx}`, `e2e/**` excluded),
`src/test/setup.ts` (jest-dom matchers + Testing Library cleanup), `playwright.config.ts` (chromium,
`testDir: e2e`, dev server via `webServer`), `e2e/smoke.spec.ts`, `src/components/ui.smoke.test.tsx`
(runner smoke), and `tsconfig.node.json` now type-checks both configs and `e2e/`.

New scripts: `npm test` (`vitest run`), `npm run test:e2e` (`playwright test`), `npm run gen:api`,
`npm run check:api`.

## 3. Dependency rules

`npm install` was run with `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` so no browser binary was fetched
(Playwright's postinstall downloads them otherwise). No other dependency was added. `npm audit` was
run for the report only: **found 0 vulnerabilities** — nothing auto-fixed.

Environment note, for the next session: the install took **21 minutes** and needed three attempts —
the first hit the 10-minute tool limit, the second died with `npm error code EIDLETIMEOUT` on
`registry.npmjs.org` after the manifest phase. The successful run reported `added 104 packages in
21m`. The registry is reachable (metadata calls answer in ~100-500 ms) but large packument/tarball
downloads are slow here (`jsdom-29.1.1.tgz` alone took 83 s).

## 4. The drift, fixed

`src/lib/display.ts`:

* **`complaintCategories` deleted.** The hand-copied list offered `plumbing`, `drainage`, `roads`,
  `garden`, `general` — none of which the API accepts — and hid `water`, `infrastructure`, `waste`,
  `parking`, `administrative`.
* **`priorityMeta` no longer carries a label.** It is now only tone + glyph, and every priority
  label comes from `displayLabel(value)`, so a value added to the contract gets a label for free
  instead of needing a second hand-written copy.
* **`trades` kept, with a comment saying why** (see deviations).

`displayLabel(value)` in `src/lib/format.ts`: `general_maintenance` → `General maintenance`,
`Pest control` for `pest_control`, and legacy free text prettified the same way (`plumbing` →
`Plumbing`, `roads` → `Roads`) so old complaint rows still display — never dropped. An empty or
blank value renders `—`.

Every screen that used the deleted list (found by grep, all updated):

| Screen | Change |
| --- | --- |
| `src/routes/Complaints.tsx` | form category + priority options from the generated enums; default category is now `complaintCategories[0]` (was the literal `plumbing`, which the API rejects); filter dropdown, table category cell and priority chip use `displayLabel` |
| `src/components/ComplaintDrawer.tsx` | subtitle and priority chip use `displayLabel` |
| `src/routes/Dashboard.tsx` | priority chip and the open-complaints category line use `displayLabel` |
| `src/routes/Providers.tsx` | **unchanged** trade filter — see deviation 1 |

`LogComplaintDrawer` is now exported from `Complaints.tsx` so a test can render the form; that is the
only change to its module surface.

## 5. Tests

Four files, **11 tests**, all passing: `src/api/generated/enums.drift.test.ts` (3 — generated values
vs `docs/openapi.json` for complaint *and* triage fields, including the `suggested_*`/`decided_*`
mirrors, plus shape checks), `src/lib/format.test.ts` (4 — the formatter, a label for **every**
generated value, legacy free text, never-empty), `src/routes/Complaints.form.test.tsx` (3 — the form
renders exactly the published categories and priorities in contract order with the right labels, and
offers no value the API would reject), `src/components/ui.smoke.test.tsx` (1 — toolchain smoke).

**Failing-first evidence.** The tests were written before the implementation. To show they actually
catch the thing they exist for, the pre-BE-1 hand-copied lists were temporarily written into
`src/api/generated/enums.ts` and the suite re-run:

```
✓ src/lib/format.test.ts (4 tests)
✓ src/components/ui.smoke.test.tsx (1 test)
  × offers no value the API would reject
  × matches the complaint fields
  × matches the triage decision and suggestion fields
Test Files  2 failed | 2 passed (4)      Tests  3 failed | 8 passed (11)
check:api — src/api/generated/enums.ts is stale: it differs from the file generated from docs/openapi.json.
check:api EXIT=1
```

`npm run gen:api` restored the file to the identical SHA-1 (`c9e113b5c0fed72435ce612a5273af6ffe41803d`),
after which the suite was green again and `check:api` exited 0. Worth noting: "renders exactly the
published categories" passed even with stale values, because it asserts the *wiring* (the form reads
the generated module) rather than the contents — the two drift tests and the "no stale value"
assertion are what catch a wrong vocabulary. Together they cover the requirement.

## 6. Verification — exact commands and results

All from `frontend/`. Timings are from the tool output.

| Command | Result |
| --- | --- |
| `npm test` | **4 test files passed, 11 tests passed**, 16.79 s, exit 0 |
| `npm run test:e2e` | **2 passed** (38.8 s), exit 0 — see below |
| `npm run typecheck` (`tsc -b --noEmit`) | exit 0 (covers `src`, both configs, and `e2e/`) |
| `npm run build` (`tsc -b && vite build`) | exit 0 — 67 modules, `dist/index.html` 0.99 kB, `dist/assets/index-OTAkGetk.css` 32.98 kB, `dist/assets/index-5hbi30RP.js` 367.62 kB (109.73 kB gzip), 18.5 s |
| `npm run gen:api` | exit 0 — `schema.d.ts` + `enums.ts` written from `docs/openapi.json` |
| `npm run check:api` | exit 0 — "the generated API files match docs/openapi.json" |
| `npm audit` | **0 vulnerabilities**, exit 0; nothing auto-fixed |
| lint | **NOT RUN — there is no linter.** No eslint dependency, no `.eslintrc*`/`eslint.config.*`, no `lint` script. The batch's "no other new dependencies" rule forbids adding one, so this is reported as a gap rather than fixed |

**The e2e smoke ran, contrary to the batch's expectation.** `npx playwright install --dry-run` showed
Playwright 1.63.0 wants chromium **v1243**, and `%LOCALAPPDATA%\ms-playwright` already contains
`chromium-1243` and `chromium_headless_shell-1243`, so no download was needed. First run: 1 failed,
1 passed — the sign-in assertion matched two headings (`<h1>Sign in</h1>` and `<h2>Welcome back</h2>`)
and Playwright's strict mode rejected the ambiguity; the assertion was made specific
(`level: 1, name: 'Sign in'`, `getByLabel('Email address')`, `getByLabel('Password')`) and the run
went green. The landing-page smoke also asserts **no console errors and no page errors**.

## Deviations, and what was deliberately left alone

1. **`trades` (provider directory filter) was NOT deleted or generated.** The batch targets the
   complaint form's lists, and the contract publishes no provider-trade vocabulary:
   `ServiceProviderResponse.trade` is `{"type": "string"}`, the column is `String(50)`, and the
   providers router takes `trade` as a free `str | None` query. The triage `TRADES` list
   (`plumber`, `electrician`, …) is a *different* vocabulary from the provider list
   (`plumbing`, `electrical`, …), so swapping in the generated triage trades would have silently
   broken the filter — worse than leaving it. It is now explicitly commented as not-contract-derived
   and is open question 1 below.
2. **`enums.ts` exists in addition to the generator's types** — reasoning in §1.
3. **The triage vocabularies are generated but not yet consumed.** AI-5's triage panel does not exist
   yet; `triageCategories`/`triagePriorities`/`triageTrades`/`triageDecisions` are there so that
   panel can read them, and both the label-coverage and drift tests cover them today.
4. **Status labels stay hand-written.** `complaintStatus`/`workOrderStatus` deliberately use
   friendlier words (`submitted` → "Logged", `reviewed` → "Under review") rather than the enum name,
   so they are presentation metadata, not a drifted value list. Their *values* are still the
   contract's. Out of this batch's scope.
5. **`src/lib/types.ts` was not regenerated from `schema.d.ts`.** The batch says not to rewrite the
   whole client, and `Complaint.category` must stay `string` precisely because legacy rows carry
   free text. The generated types are available for future work.
6. No backend file was edited; `docs/openapi.json` was read, never written.

## Written, not run

Nothing in this batch is written-but-not-run. The unit tests, the label and drift guards, `check:api`,
`gen:api`, `tsc`, the production build and the Playwright smoke all ran and are reported above. What
they do **not** cover:

* The complaint form was verified by component test, **not** in a real browser: the drawer needs a
  signed-in resident with a linked unit and a live API, and no backend was started for this batch.
  The e2e smoke covers only the public shell (landing page, sign-in form).
* No browser was downloaded, so `e2e` runs only on machines that already have chromium v1243.

## Open questions

1. **Provider trades need a backend vocabulary.** Until `ServiceProviderResponse.trade` is an enum,
   `trades` in `display.ts` cannot be generated and will keep drifting from the directory's data.
2. **Should the enum options be a fetched resource instead of generated constants?** Generated
   constants are stale the moment the contract changes without a regeneration; `check:api` is the
   guard, and it only runs when someone runs it. Wiring it into CI is a one-line follow-up.
3. **Node version.** vitest 5 needs `^22.12 || ^24 || >=26`, and jsdom 30 needed `>=24.15`. If CI
   pins an older Node, the pinned versions here may not install — worth aligning deliberately.
4. **The 14-day freshness rule is a deliberate lag**: these pins miss security patches published in
   the last two weeks by design, and should be bumped on a schedule rather than ad hoc.

## Files changed (all under `frontend/`)

| File | Change |
| --- | --- |
| `package.json` | 7 exact dev dependencies; `test`, `test:e2e`, `gen:api`, `check:api` scripts |
| `package-lock.json` | rewritten by npm (104 packages added) |
| `vitest.config.ts` | **new** — unit/component runner config |
| `playwright.config.ts` | **new** — e2e runner config |
| `tsconfig.node.json` | also type-checks the new configs and `e2e/` |
| `src/test/setup.ts` | **new** — jest-dom matchers + cleanup |
| `scripts/gen-api.mjs` | **new** — contract → `schema.d.ts` + `enums.ts` |
| `scripts/check-api.mjs` | **new** — drift guard |
| `src/api/generated/schema.d.ts` | **new, generated** — 3,079 lines of contract types |
| `src/api/generated/enums.ts` | **new, generated** — the six runtime vocabularies |
| `src/api/generated/enums.drift.test.ts` | **new** — generated vs published enums |
| `src/lib/format.ts` | `displayLabel()` added |
| `src/lib/format.test.ts` | **new** — label coverage + legacy free text |
| `src/lib/display.ts` | `complaintCategories` deleted; `priorityMeta` reduced to tone/glyph; `trades` annotated |
| `src/routes/Complaints.tsx` | form + filter + table use the generated enums and `displayLabel`; `LogComplaintDrawer` exported |
| `src/routes/Complaints.form.test.tsx` | **new** — the form's options |
| `src/routes/Dashboard.tsx` | `displayLabel` for priority and category |
| `src/components/ComplaintDrawer.tsx` | `displayLabel` for priority and category |
| `src/components/ui.smoke.test.tsx` | **new** — toolchain smoke |
| `e2e/smoke.spec.ts` | **new** — landing + sign-in smoke |
