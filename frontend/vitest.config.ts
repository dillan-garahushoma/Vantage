import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

/**
 * Unit/component tests (Vitest + React Testing Library, jsdom).
 *
 * `npm run test:e2e` is separate: Playwright owns `e2e/**`, which is excluded here
 * so the two runners never collect each other's specs.
 */
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
    exclude: ['node_modules/**', 'dist/**', 'e2e/**'],
    setupFiles: ['./src/test/setup.ts'],
    restoreMocks: true,
    // jsdom is expensive to construct (~8s per file here) and these are
    // interaction tests, so the whole file's budget is shared with the runner
    // rather than the 5s default. Assertions are unchanged.
    testTimeout: 15_000,
    // One jsdom per worker instead of one per file: the component specs each
    // spin up a fresh environment, and the construction cost dominated the run.
    pool: 'vmThreads',
  },
})
