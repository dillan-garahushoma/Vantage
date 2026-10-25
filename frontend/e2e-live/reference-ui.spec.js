/** Live reads and UI interactions. Run only against isolated demo fixtures. */
import { expect, test } from '@playwright/test';
import { ADMIN, PROVIDER, RESIDENT, signIn } from './helpers';

const screens = {
  admin: ['/app', '/app/complaints', '/app/work-orders', '/app/incidents', '/app/health', '/intelligence', '/app/providers', '/app/properties', '/app/announcements', '/admin/members', '/admin/residency', '/admin/settings', '/admin/setup', '/app/notifications'],
  resident: ['/app', '/app/complaints', '/app/incidents', '/app/health', '/intelligence', '/app/providers', '/app/properties', '/app/announcements', '/app/notifications'],
  provider: ['/provider/work', '/app/work-orders', '/intelligence', '/app/announcements', '/app/health', '/app/notifications'],
};

for (const [role, account] of Object.entries({ admin: ADMIN, resident: RESIDENT, provider: PROVIDER })) {
  test(`${role} workspace routes load real estate data without browser errors or overflow`, async ({ page }, testInfo) => {
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await signIn(page, account);
    for (const route of screens[role]) {
      await page.goto(route);
      await expect(page.locator('main')).toBeVisible();
      await expect(page.getByText('Loading your estates')).toHaveCount(0);
      await page.waitForLoadState('networkidle');
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), route).toBe(true);
      await expect(page.getByRole('heading', { name: /page not found|something went wrong/i })).toHaveCount(0);
      await expect(page.getByText(/Cannot reach the VALORA API/)).toHaveCount(0);
      if (route === '/app' || route === '/intelligence' || route === '/provider/work') {
        await page.screenshot({ path: testInfo.outputPath(`${role}-${route.replaceAll('/', '-')}.png`), fullPage: true });
      }
    }
    expect(errors).toEqual([]);
  });
}

test('workspace search supports keyboard activation and the drawer closes with Escape', async ({ page }, testInfo) => {
  await signIn(page, ADMIN);
  await page.goto('/app');
  if (testInfo.project.name === 'desktop') {
    await page.getByRole('textbox', { name: 'Search the estate workspace' }).fill('work orders');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/\/app\/work-orders$/);
  }
  await page.getByRole('button', { name: 'Create work order', exact: true }).first().click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toBeHidden();
});

test('the assistant returns grounded estate records with the optional LLM off', async ({ page }) => {
  await signIn(page, ADMIN);
  await page.goto('/intelligence');
  await page.getByRole('textbox', { name: 'Ask VALORA a question' }).fill('Which maintenance issues need attention?');
  await page.getByRole('button', { name: 'Send question', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Ask VALORA Intelligence' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Copy answer' })).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
  await page.getByRole('button', { name: 'Expand chat' }).click();
  await expect(page.getByRole('dialog')).toContainText(/work order|stored|record/i);
  await expect(page.getByRole('textbox', { name: 'Ask VALORA a question' })).toBeEnabled();
});
