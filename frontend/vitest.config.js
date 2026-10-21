import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';
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
        include: ['src/**/*.test.{js,jsx}'],
        exclude: ['node_modules/**', 'dist/**', 'e2e/**'],
        setupFiles: ['./src/test/setup.js'],
        restoreMocks: true,
        // jsdom is expensive to construct (~8s per file here) and these are
        // interaction tests, so the whole file's budget is shared with the runner
        // rather than the 5s default. Assertions are unchanged.
        testTimeout: 15_000,
        // Separate worker processes avoid the VM-thread startup stall observed
        // on the local Windows runtime during the JavaScript migration.
        pool: 'forks',
        maxWorkers: 2,
    },
});
