import { expect, test } from '@playwright/test';
/**
 * The onboarding journey, driven through the real UI against a real backend.
 *
 * It is deliberately self-sufficient: every account is created here, with an email
 * derived from the run's stamp, so the spec can run against a shared development
 * database repeatedly without a seed and without colliding with an earlier run.
 * The one thing it needs is a running API whose `VITE_API_BASE_URL` this dev
 * server points at — see `playwright.live.config.js`.
 *
 * The four tests are a sequence: the first creates the estate the others exercise.
 * They therefore must run as a file (`workers: 1`, `fullyParallel: false`), and the
 * later ones skip with a clear message if the administrator from the first test is
 * not there. Run with `E2E_BASE_URL=… npm run test:e2e:live`.
 */
const PASSWORD = 'ValoraJourney2026!';
const stamp = process.env.JOURNEY_STAMP ?? String(Date.now()).slice(-9);
const ADMIN = { email: `journey-admin-${stamp}@example.co.za`, name: 'Nomvula Dlamini' };
const RESIDENT = { email: `journey-resident-${stamp}@example.co.za`, name: 'Thandi Nkosi' };
const PROVIDER = { email: `journey-provider-${stamp}@example.co.za`, name: 'Sipho Mokoena' };
const ESTATE = {
    name: `Ridge Close Journey ${stamp}`,
    suburb: 'Centurion',
    city: 'Tshwane',
    province: 'Gauteng',
    description: 'A 24-unit complex with a shared pool and a single monitored gate.',
};
const UNIT_A = 'T-101';
const UNIT_B = 'T-102';
/* --------------------------------------------------------------- session */
/**
 * Ends the session. The shell's own sign-out button is used when the screen has
 * one — that is the path a person takes — and localStorage is cleared as well, so
 * a spec that continues from a screen without the button still starts clean.
 * (Signing out from an onboarding screen lands on the sign-in page, because that
 * screen redirects a session-less visitor there; the landing page and the sign-in
 * page are both fine destinations for the next step.)
 */
async function signOut(page) {
    const button = page.getByRole('button', { name: 'Sign out' });
    if ((await button.count()) > 0) {
        await button.first().click();
        await expect(page).toHaveURL(/\/(login)?$/, { timeout: 20_000 });
    }
    await page.evaluate(() => localStorage.clear());
}
async function signIn(page, email) {
    // Two navigations on purpose. The app returns you to where you were before it
    // sent you here (`location.state.from`, set when a protected screen redirects),
    // and a browser reload of the same URL keeps that history entry's state. An
    // intermediate page makes the next `/login` a fresh entry with no deep link, so
    // the sign-in lands wherever the account actually belongs.
    await page.goto('/estates');
    await page.goto('/login');
    await page.getByLabel('Email address').fill(email);
    await page.getByLabel('Password').fill(PASSWORD);
    await page.getByRole('button', { name: 'Sign in' }).click();
}
/**
 * Signs in as the administrator this run created, and skips the test — rather
 * than failing after two minutes of waiting — when that account is not there.
 */
async function signInAsAdmin(page) {
    await signOut(page);
    await signIn(page, ADMIN.email);
    const arrived = await page
        .waitForURL(/\/(welcome|admin\/setup|app|join|provider\/waiting)$/, { timeout: 30_000 })
        .then(() => true)
        .catch(() => false);
    if (!arrived && (await page.getByText(/invalid email or password/i).count()) > 0) {
        test.skip(true, `no administrator for stamp ${stamp}: run the whole file in order, or let the first test create it`);
    }
    await expect(page).toHaveURL(/\/admin\/setup/, { timeout: 30_000 });
}
/** Registers an estate administrator and the estate in one step. */
async function registerEstateAdmin(page) {
    await page.goto('/register');
    await page.getByRole('radio', { name: 'Estate administrator', exact: true }).check();
    await page.getByLabel('Full name').fill(ADMIN.name);
    await page.getByLabel('Email address').fill(ADMIN.email);
    await page.getByLabel('Password').fill(PASSWORD);
    await page.getByLabel('Estate name').fill(ESTATE.name);
    await page.getByLabel('Suburb').fill(ESTATE.suburb);
    await page.getByLabel('City').fill(ESTATE.city);
    await page.getByLabel('Province').selectOption(ESTATE.province);
    await page.getByLabel('Description (optional)').fill(ESTATE.description);
    await page.getByRole('button', { name: /create account and register the estate/i }).click();
}
async function registerResident(page) {
    await page.goto('/register');
    await page.getByRole('radio', { name: 'Resident', exact: true }).check();
    await page.getByLabel('Full name').fill(RESIDENT.name);
    await page.getByLabel('Email address').fill(RESIDENT.email);
    await page.getByLabel('Password').fill(PASSWORD);
    await page.getByRole('button', { name: /create account$/i }).click();
}
async function registerProvider(page) {
    await page.goto('/register');
    await page.getByRole('radio', { name: 'Service provider', exact: true }).check();
    await page.getByLabel('Full name').fill(PROVIDER.name);
    await page.getByLabel('Email address').fill(PROVIDER.email);
    await page.getByLabel('Password').fill(PASSWORD);
    await page.getByLabel('Trade').fill('plumbing');
    await page.getByLabel('Contact phone').fill('082 000 0000');
    await page.getByRole('button', { name: /create account$/i }).click();
}
/** The estate's one live join code, as the setup screen shows it. */
async function readJoinCode(page) {
    const card = page.locator('section', { has: page.getByRole('heading', { name: 'Join code' }) });
    const code = (await card.locator('p.num').first().textContent())?.trim() ?? '';
    expect(code, 'the setup screen must show one live join code').toMatch(/^[A-Z0-9]{10}$/);
    return code;
}
test.describe('onboarding journey', () => {
    test('an estate administrator can register the estate and finish the checklist', async ({ page, }) => {
        const problems = [];
        page.on('pageerror', (error) => problems.push(`pageerror: ${error.message}`));
        await registerEstateAdmin(page);
        // /welcome resolves the destination from membership: an administrator of a
        // brand-new estate belongs on the setup checklist.
        await expect(page).toHaveURL(/\/admin\/setup/, { timeout: 30_000 });
        await expect(page.getByRole('heading', { level: 1 })).toContainText(ESTATE.name);
        // One of five: the description travelled with the registration itself.
        await expect(page.getByText('1 of 5', { exact: false })).toBeVisible();
        await expect(page.getByText('Describe the estate')).toBeVisible();
        // 1. The description. Field labels carry their hint inside the same label, so
        //    these are anchored matches on the control's role and name.
        await page.getByRole('textbox', { name: /^Description/ }).fill(ESTATE.description);
        await page.getByRole('button', { name: 'Save description' }).click();
        await expect(page.getByText('Saved.')).toBeVisible();
        // 2. Units, pasted as a list.
        await page
            .getByRole('textbox', { name: /^Units/ })
            .fill(`${UNIT_A}, 12 Ridge Close, 96, 3, 2\n${UNIT_B}, 14 Ridge Close, 88, 2, 2`);
        await page.getByRole('button', { name: 'Add units' }).click();
        await expect(page.getByText('Added 2 units.')).toBeVisible();
        // 3. A join code, which is what a resident will redeem.
        await page.getByRole('button', { name: /issue a code/i }).click();
        const code = await readJoinCode(page);
        expect(code).toHaveLength(10);
        // 4. A photograph, uploaded the way an administrator would: the file input is
        //    visually hidden behind the drop zone, and the caption is set first.
        await page.getByRole('textbox', { name: /^Caption/ }).fill('The pool at dusk');
        await page
            .getByLabel('Choose a photograph to upload')
            .setInputFiles('e2e-live/fixtures/pool.jpg');
        await expect(page.getByText('1 of 12 uploaded')).toBeVisible({ timeout: 30_000 });
        await expect(page.getByText('The pool at dusk')).toBeVisible();
        // 5. Publishing, which is what makes the estate findable at all. These are
        //    controlled checkboxes that follow the server's answer, so the box moves
        //    when the PATCH lands rather than on the click — hence `click()` and a
        //    polled assertion instead of `check()`.
        await page.getByLabel(/list this estate in the public directory/i).click();
        await expect(page.getByLabel(/list this estate in the public directory/i)).toBeChecked({
            timeout: 30_000,
        });
        // The checklist now reports all five steps done, from the API's own values.
        await expect(page.getByText('5 of 5', { exact: false })).toBeVisible({ timeout: 30_000 });
        // The join code survives a reload: it is the estate's, not the screen's state.
        await page.reload();
        expect(await readJoinCode(page)).toBe(code);
        expect(problems).toEqual([]);
    });
    test('the published estate is visible to a visitor with no account', async ({ page }) => {
        const problems = [];
        page.on('pageerror', (error) => problems.push(`pageerror: ${error.message}`));
        // No session at all: this is the unauthenticated directory.
        await page.goto('/estates');
        await page.getByLabel(/search by name, suburb or city/i).fill(ESTATE.name);
        await page.getByRole('button', { name: 'Search' }).click();
        const card = page.locator('li', { hasText: ESTATE.name }).first();
        await expect(card).toBeVisible({ timeout: 30_000 });
        await expect(card.getByText(/2 units/)).toBeVisible();
        await card.getByRole('link', { name: /view this complex/i }).click();
        await expect(page.getByRole('heading', { level: 1, name: ESTATE.name })).toBeVisible();
        await expect(page.getByText(ESTATE.description)).toBeVisible();
        // The score is a separate decision and this estate never published one.
        await expect(page.getByText('Living Score')).toHaveCount(0);
        // And nothing about the units, residents or complaints is published.
        await expect(page.getByText(UNIT_A)).toHaveCount(0);
        await expect(page.getByText(UNIT_B)).toHaveCount(0);
        expect(problems).toEqual([]);
    });
    test('a resident joins with the code, and their complaint is recorded', async ({ page }) => {
        const problems = [];
        page.on('pageerror', (error) => problems.push(`pageerror: ${error.message}`));
        await registerResident(page);
        // A new resident has no estate, so role routing sends them to redeem a code.
        await expect(page).toHaveURL(/\/join/, { timeout: 30_000 });
        // The administrator reads the live code; a resident never sees it until a code
        // is handed to them.
        await signInAsAdmin(page);
        const code = await readJoinCode(page);
        await signOut(page);
        await signIn(page, RESIDENT.email);
        await expect(page).toHaveURL(/\/join/, { timeout: 30_000 });
        await page.getByRole('textbox', { name: /^Join code/ }).fill(code);
        await page.getByRole('textbox', { name: /^Unit number/ }).fill(UNIT_A);
        await page.getByRole('button', { name: /join the estate/i }).click();
        await expect(page).toHaveURL(/\/app$/, { timeout: 30_000 });
        await expect(page.getByRole('option', { name: ESTATE.name })).toHaveCount(1);
        // The resident logs a complaint against their unit.
        await page.goto('/app/complaints');
        // Two of these exist on a resident's complaints screen (the header and the
        // empty-state action) and they open the same drawer.
        await page.getByRole('button', { name: 'Log a complaint' }).first().click();
        const dialog = page.getByRole('dialog');
        await expect(dialog).toBeVisible();
        // The estate holds exactly the two units this journey registered, so the first
        // real option (index 0 is “Select a unit…”) is the resident's own.
        await dialog.getByLabel('Which unit?').selectOption({ index: 1 });
        await dialog.getByLabel('Category').selectOption('water');
        await dialog.getByLabel('Priority').selectOption('high');
        await dialog
            .getByLabel('What is wrong?')
            .fill('Sewage overflow at the Block C boundary — pooling near the pedestrian gate.');
        await dialog.getByRole('button', { name: 'Log complaint' }).click();
        await expect(dialog).toBeHidden({ timeout: 30_000 });
        const row = page.locator('tbody tr', { hasText: /sewage overflow/i }).first();
        await expect(row).toBeVisible();
        await expect(row.getByText('Logged')).toBeVisible();
        expect(problems).toEqual([]);
    });
    test('a provider waits to be added, and the administrator adds them by email', async ({ page, }) => {
        const problems = [];
        page.on('pageerror', (error) => problems.push(`pageerror: ${error.message}`));
        await registerProvider(page);
        // A provider cannot add themselves to an estate: the screen says so.
        await expect(page).toHaveURL(/\/provider\/waiting/, { timeout: 30_000 });
        await expect(page.getByRole('heading', { name: /waiting to be added to an estate/i })).toBeVisible();
        await expect(page.getByText(/Plumbing/)).toBeVisible();
        await signInAsAdmin(page);
        await page.goto('/admin/members');
        await expect(page.getByText(RESIDENT.name)).toBeVisible({ timeout: 30_000 });
        await page.getByRole('textbox', { name: /^Provider email/ }).fill(PROVIDER.email);
        await page.getByRole('button', { name: /add provider/i }).click();
        await expect(page.getByText(/can now be assigned work in this estate/i)).toBeVisible({
            timeout: 30_000,
        });
        await expect(page.locator('tbody tr', { hasText: PROVIDER.name })).toContainText('Service provider');
        // The provider now has an estate, and no work yet — which the screen says plainly.
        await signOut(page);
        await signIn(page, PROVIDER.email);
        await expect(page).toHaveURL(/\/app$/, { timeout: 30_000 });
        await page.goto('/provider/work');
        await expect(page.getByText('Nothing assigned to you yet')).toBeVisible({ timeout: 30_000 });
        expect(problems).toEqual([]);
    });
});
