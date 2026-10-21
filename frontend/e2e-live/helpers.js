import { expect } from '@playwright/test';
/**
 * The demo fixture accounts created by `python -m app.cli seed-demo`.
 *
 * They exist only in the demonstration database (the seeder refuses any database
 * whose name does not contain "demo"), the addresses are on `example.com`, and the
 * password is the seeder's documented local-only default. The one account that
 * owns two units in the same estate is `resident01` — the ADR-007 rule that a
 * resident may hold more than one unit.
 */
export const ADMIN = { email: 'admin@example.com', password: 'ValoraDemo123!' };
export const RESIDENT = { email: 'resident01@example.com', password: 'ValoraDemo123!' };
export const PROVIDER = { email: 'provider01@example.com', password: 'ValoraDemo123!' };
/**
 * Signs in through the real form. Where the account *lands* is the role routing's
 * decision (an HOA administrator goes to the setup checklist, a resident without
 * an estate to the join screen, a provider without one to the waiting screen), so
 * this waits for any of those destinations rather than a single one.
 */
export async function signIn(page, who) {
    await page.goto('/login');
    await page.getByLabel('Email address').fill(who.email);
    await page.getByLabel('Password').fill(who.password);
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page).toHaveURL(/\/(welcome|app|admin\/setup|join|provider\/waiting)$/, { timeout: 30_000 });
}
/** Signs in and opens the estate dashboard, wherever the routing landed first. */
export async function signInToDashboard(page, who) {
    await signIn(page, who);
    await page.goto('/app');
}
/**
 * Ends one session and starts another. `localStorage.clear()` runs first so the
 * sign-in page is a fresh entry: the app returns you to where you were before a
 * protected screen redirected you, and a stale deep link would send the next role
 * somewhere it cannot read.
 */
export async function switchUser(page, who) {
    // The landing page first: `localStorage` cannot be touched on about:blank, and a
    // fresh tab starts there.
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await signIn(page, who);
}
/**
 * Watches the console and the network for the things a wiring check is for:
 * uncaught exceptions, console errors, and server-side failures. A 503 carrying
 * the AI layer's own code is expected when AI is switched off, so it is not
 * counted as a failure — the point of that state is that the product still works.
 */
export function watchForErrors(page) {
    const problems = [];
    page.on('pageerror', (error) => problems.push(`pageerror: ${error.message}`));
    page.on('console', (message) => {
        if (message.type() !== 'error')
            return;
        // A 404 on "no suggestion stored yet" is a designed state, and Chromium
        // logs every failed resource fetch as a console error. The network watcher
        // below is the one that judges statuses.
        if (/Failed to load resource/.test(message.text()))
            return;
        problems.push(`console: ${message.text()}`);
    });
    page.on('response', (response) => {
        if (response.status() < 500)
            return;
        void response
            .text()
            .then((body) => {
            const unavailable = response.status() === 503 && body.includes('AI_UNAVAILABLE');
            if (!unavailable) {
                problems.push(`${response.status()} ${response.url()}`);
            }
        })
            .catch(() => problems.push(`${response.status()} ${response.url()} (no body)`));
    });
    return problems;
}
/**
 * The automated estate brief, addressed by its own heading.
 *
 * It is a `<section>` so a caretaker looking for the panel gets the whole panel and
 * never the sidebar or an unrelated block that happens to share a word.
 */
export function briefPanel(page) {
    return page.locator('section', {
        has: page.getByRole('heading', { name: 'Estate health brief' }),
    });
}
/** The dashboard's Living Score card, addressed by its own heading. */
export function livingScorePanel(page) {
    return page.locator('section', {
        has: page.getByRole('heading', { name: 'Estate quality of life' }),
    });
}
/**
 * Opens a complaint the HOA can actually ask the AI layer about.
 *
 * The API only produces a triage suggestion for a complaint that is `submitted` or
 * `reviewed`, and it refuses anything else — so the register's own status filter is
 * used to show only those, rather than walking the newest rows and hoping. A shared
 * demonstration database drifts (every journey run files a complaint that ends up
 * `rated`), which is exactly why picking "the first row" is not good enough.
 */
export async function openTriableComplaint(page) {
    const dialog = page.getByRole('dialog');
    const rows = page.locator('tbody tr');
    const statusFilter = page.getByLabel('Status');
    for (const status of ['Logged', 'Under review']) {
        await statusFilter.selectOption({ label: status });
        // `count()` does not wait for the filtered list, so wait for either a row or
        // the empty state before deciding.
        const listed = await rows
            .first()
            .waitFor({ state: 'visible', timeout: 45_000 })
            .then(() => true)
            .catch(() => false);
        if (!listed)
            continue;
        await rows.first().click();
        await expect(dialog).toBeVisible();
        // The detail loads after the drawer opens, so wait for the triage section
        // rather than sampling it once: an immediate `isVisible()` would see the
        // loading state and walk past an eligible complaint.
        const appeared = await dialog
            .getByRole('heading', { name: 'AI triage' })
            .waitFor({ state: 'visible', timeout: 15_000 })
            .then(() => true)
            .catch(() => false);
        if (appeared)
            return dialog;
        await page.getByRole('button', { name: 'Close', exact: true }).first().click();
        await expect(dialog).toBeHidden();
    }
    throw new Error('no submitted or reviewed complaint in the register to triage');
}
