import { defineConfig, devices } from '@playwright/test'

// The Playwright runner is Node, but this project deliberately carries no
// `@types/node` (the app itself is browser-only), so declare the one global
// this config reads and nothing more.
declare const process: { env: Record<string, string | undefined> }

/**
 * The live wiring check — `npm run test:e2e:live`.
 *
 * These specs drive a **real backend** against a seeded database, so they are
 * kept out of `playwright.config.ts` (whose smoke run must never need an API)
 * and out of `e2e/`. Point one at whatever pair you are running:
 *
 * ```text
 * E2E_BASE_URL=http://localhost:5199 npm run test:e2e:live
 * ```
 *
 * The base URL must be a dev server whose `VITE_API_BASE_URL` points at the
 * backend under test. Nothing here starts a server: the operator does, so the
 * spec can never silently fall back to a different estate or a stale database.
 */
// One stamp per invocation, handed to the specs through the environment. A spec
// that creates its own accounts names them per invocation; sharing the stamp means
// a worker restart mid-run cannot invent a second set of them.
process.env.JOURNEY_STAMP ??= String(Date.now()).slice(-9)

export default defineConfig({
  testDir: './e2e-live',
  fullyParallel: false,
  workers: 1,
  forbidOnly: true,
  // The first page load against a cold dev server has to transform the whole
  // module graph, which is a property of the tooling rather than of the UI.
  timeout: 180_000,
  expect: { timeout: 45_000 },
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:5173',
    trace: 'retain-on-failure',
  },
  // The acceptance journey runs at both widths. `mobile` is the phone viewport the
  // responsive sweep uses (390 x 844) in the same browser the desktop run uses, so
  // both runs need the same one browser and the same one backend.
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    {
      name: 'mobile',
      use: {
        browserName: 'chromium',
        viewport: { width: 390, height: 844 },
        deviceScaleFactor: 3,
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
})
