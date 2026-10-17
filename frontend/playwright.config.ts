import { defineConfig, devices } from '@playwright/test'

/**
 * End-to-end smoke tests — `npm run test:e2e`.
 *
 * Playwright is deliberately separate from Vitest: it owns `e2e/**`, and the
 * Vitest run excludes that directory so neither runner collects the other's
 * specs. The dev server is started (or reused) automatically.
 *
 * Browsers are not downloaded by this project's tooling. Run
 * `npx playwright install chromium` once locally before the first e2e run.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: true,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
  },
})
