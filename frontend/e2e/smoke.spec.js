import { expect, test } from '@playwright/test';
/**
 * End-to-end smoke: the built client boots against the dev server, renders the
 * public shell, and logs no console errors.
 *
 * NOT RUN in the batch that added it: Playwright browser binaries are not
 * downloaded by this project's tooling (see playwright.config.js). Run
 * `npx playwright install chromium` and then `npm run test:e2e`.
 */
test('the landing page renders without console errors', async ({ page }) => {
    const consoleErrors = [];
    page.on('console', (message) => {
        if (message.type() === 'error')
            consoleErrors.push(message.text());
    });
    page.on('pageerror', (error) => consoleErrors.push(error.message));
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 1, name: /understand how your complex is being cared for/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /find your complex/i })).toBeVisible();
    expect(consoleErrors).toEqual([]);
});
test('the sign-in route renders its form', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { level: 1, name: 'Sign in' })).toBeVisible();
    await expect(page.getByLabel('Email address')).toBeVisible();
    await expect(page.getByLabel('Password')).toBeVisible();
});
