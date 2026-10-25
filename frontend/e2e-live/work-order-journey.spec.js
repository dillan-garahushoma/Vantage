import { expect, test } from '@playwright/test';
import { ADMIN, PROVIDER, RESIDENT, livingScorePanel, switchUser, watchForErrors, } from './helpers';
/**
 * The acceptance journey: one issue, worked to a resolution by three people.
 *
 * It runs against the **seeded demonstration database** and drives the real UI:
 *
 *   resident logs it → the HOA reviews it and assigns a provider (assigning is
 *   what creates the work order) → the provider starts and completes the work →
 *   the resident rates it → the HOA recalculates the Living Score and the
 *   dashboard shows the stored number.
 *
 * Every step is a screen a person uses, and every figure asserted comes from the
 * API: the spec never computes a score, and it fails if the console or the
 * network reports anything the product should not be doing. One screenshot per
 * step lands in `docs/acceptance/` as the evidence for the acceptance report,
 * named after the project so the desktop and mobile runs sit side by side.
 *
 * The complaint carries a per-invocation, per-project marker, so the same
 * database can be used repeatedly and by both widths.
 */
const stamp = process.env.JOURNEY_STAMP ?? String(Date.now()).slice(-9);
test('an issue is assigned, worked, rated and recalculated end to end', async ({ page, }, testInfo) => {
    const problems = watchForErrors(page);
    const marker = `E2E-${stamp}-${testInfo.project.name}`;
    const description = `Burst pipe under the kitchen sink (${marker}) — water pooling in the passage.`;
    const shot = (name) => page.screenshot({ path: testInfo.outputPath(`${name}.png`) });
    const complaintRecord = () => testInfo.project.name === 'mobile'
        ? page.getByRole('button').filter({ hasText: marker })
        : page.locator('tbody tr', { hasText: marker });
    /**
     * A phone must not be able to scroll sideways. This is measured on the real
     * screen with real data: a mock-API sweep cannot see an overflow caused by a
     * long complaint description, which is exactly what happened on the dashboard
     * before the cards were made shrinkable.
     */
    const assertNoHorizontalOverflow = async (where) => {
        if (testInfo.project.name !== 'mobile')
            return;
        const measured = await page.evaluate(() => ({
            scrollWidth: document.documentElement.scrollWidth,
            clientWidth: document.documentElement.clientWidth,
        }));
        console.log(`overflow@${where}: scrollWidth=${measured.scrollWidth} clientWidth=${measured.clientWidth}`);
        expect(measured.scrollWidth, `the page is wider than its ${measured.clientWidth}px viewport at ${where}`).toBeLessThanOrEqual(measured.clientWidth);
    };
    /* ------------------------------------------------ the resident logs it */
    await switchUser(page, RESIDENT);
    await page.goto('/app/complaints');
    await page.locator('header').getByRole('button', { name: 'Log a complaint', exact: true }).click();
    const logForm = page.getByRole('dialog');
    await expect(logForm.getByRole('heading', { name: 'Log a complaint' })).toBeVisible();
    await logForm.getByLabel('Which unit?').selectOption({ index: 1 });
    await logForm.getByLabel('Category').selectOption('water');
    await logForm.getByLabel('Priority').selectOption('urgent');
    await logForm.getByLabel('What is wrong?').fill(description);
    await logForm.getByRole('button', { name: 'Log complaint' }).click();
    await expect(logForm).toBeHidden({ timeout: 30_000 });
    const residentRow = complaintRecord();
    await expect(residentRow).toBeVisible({ timeout: 30_000 });
    await assertNoHorizontalOverflow('the resident complaint list');
    // The list carries the reference in its first cell; the drawer's own title is
    // the same number, which is what a person reads there.
    const rowText = (await residentRow.textContent()) ?? '';
    const complaintId = Number((rowText.match(/#(\d+)/) ?? ['', ''])[1]);
    expect(complaintId).toBeGreaterThan(0);
    await residentRow.click();
    const residentDrawer = page.getByRole('dialog');
    await expect(residentDrawer.getByRole('heading', { name: `Issue details · #${complaintId}` })).toBeVisible({ timeout: 30_000 });
    // The resident's own view of the repair: honest about there being none yet.
    await expect(residentDrawer.getByText(/No work order has been raised/)).toBeVisible({
        timeout: 30_000,
    });
    await shot('01-resident-logs-and-sees-no-work-order');
    await residentDrawer.getByRole('button', { name: 'Close', exact: true }).first().click();
    /* ------------------------------------------------- the HOA assigns it */
    await switchUser(page, ADMIN);
    await page.goto('/app/complaints');
    const adminRow = complaintRecord();
    await expect(adminRow).toBeVisible({ timeout: 30_000 });
    await adminRow.click();
    const adminDrawer = page.getByRole('dialog');
    await adminDrawer.getByRole('button', { name: 'Mark under review' }).click();
    await expect(adminDrawer.getByText('Under review', { exact: true })).toBeVisible({
        timeout: 30_000,
    });
    // Assigning a provider is what creates the work order. Sipho Dlamini is a
    // member of this estate, so the estate-scoped directory offers him.
    const providerSelect = adminDrawer.getByLabel(/Verified provider/);
    await expect(providerSelect).toBeVisible({ timeout: 30_000 });
    const sipho = providerSelect.locator('option', { hasText: 'Sipho Dlamini' });
    const siphoValue = await sipho.getAttribute('value');
    expect(siphoValue).not.toBeNull();
    await providerSelect.selectOption(siphoValue);
    await adminDrawer.getByRole('button', { name: 'Assign provider' }).click();
    const workOrderRef = adminDrawer.getByText(/WO-\d{4}/).first();
    await expect(workOrderRef).toBeVisible({ timeout: 30_000 });
    const workOrderLabel = (await workOrderRef.textContent()) ?? '';
    const workOrderId = Number(workOrderLabel.replace(/\D/g, ''));
    expect(workOrderId).toBeGreaterThan(0);
    await shot('02-admin-assigns-the-provider');
    await adminDrawer.getByRole('button', { name: 'Close', exact: true }).first().click();
    /* ------------------------------------------- the provider does the work */
    await switchUser(page, PROVIDER);
    await page.goto('/provider/work');
    // The provider's own list, newest first: this is the job just created for them.
    const job = page.locator('li', { hasText: `WO-${String(workOrderId).padStart(4, '0')}` });
    await expect(job).toBeVisible({ timeout: 45_000 });
    await job.getByRole('button', { name: 'Start this work' }).click();
    await expect(job.getByRole('button', { name: 'Mark as completed' })).toBeVisible({
        timeout: 30_000,
    });
    await job.getByRole('button', { name: 'Mark as completed' }).click();
    await job
        .getByLabel(/What was done/)
        .fill('Replaced the failed section of pipe and pressure-tested the line.');
    await shot('03-provider-completes-the-work');
    await job.getByRole('button', { name: 'Complete this job' }).click();
    await expect(job.getByText('Replaced the failed section of pipe')).toBeVisible({
        timeout: 30_000,
    });
    /* -------------------------------------------------- the resident rates it */
    await switchUser(page, RESIDENT);
    await page.goto('/app/complaints');
    const ratedRow = complaintRecord();
    await expect(ratedRow).toBeVisible({ timeout: 30_000 });
    await ratedRow.click();
    const ratingDrawer = page.getByRole('dialog');
    // The completion note is on the work-order panel *and* in the append-only
    // lifecycle rail, which is exactly what an audit trail should do.
    await expect(ratingDrawer.getByText('Replaced the failed section of pipe').first()).toBeVisible({
        timeout: 30_000,
    });
    await ratingDrawer.getByRole('button', { name: /Rate the repair 5 out of 5/ }).click();
    await expect(ratingDrawer.getByText(/You rated this repair 5 out of 5/)).toBeVisible({
        timeout: 30_000,
    });
    await shot('04-resident-rates-the-repair');
    await ratingDrawer.getByRole('button', { name: 'Close', exact: true }).first().click();
    /* ------------------------------------- the HOA recalculates the score */
    await switchUser(page, ADMIN);
    await page.goto('/app');
    const panel = livingScorePanel(page);
    await expect(panel.getByText('Estate health', { exact: true })).toBeVisible();
    // The stored score is calculated by the engine; no seeded-data label is
    // presented as part of the live operational UI.
    await expect(panel.getByText('Demo data')).toHaveCount(0);
    await expect(panel.getByText(/\/ 100/).first()).toBeVisible({ timeout: 45_000 });
    await shot('05-dashboard-shows-the-score');
    await assertNoHorizontalOverflow('the administrator dashboard');
    // The recalculation is a real request that appends a snapshot; the panel then
    // re-reads the stored one. No client-side arithmetic is involved at any point.
    const recalculated = page.waitForResponse((response) => response.url().includes('/api/v1/analytics/living-score/recalculate') &&
        response.request().method() === 'POST', { timeout: 60_000 });
    await panel.getByRole('button', { name: /^Recalculate$/ }).click();
    const recalculationResponse = await recalculated;
    expect(recalculationResponse.status()).toBe(201);
    const stored = await recalculationResponse.json();
    await expect(panel.getByText(Number(stored.overall_score).toLocaleString('en-ZA', { maximumFractionDigits: 1 }), { exact: true })).toBeVisible({ timeout: 60_000 });
    await expect(panel.getByText(/^Updated /)).toBeVisible();
    await expect(panel.getByText(/\/ 100/).first()).toBeVisible();
    await shot('06-dashboard-after-recalculation');
    expect(problems).toEqual([]);
});
