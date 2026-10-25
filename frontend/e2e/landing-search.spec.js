import { expect, test } from '@playwright/test';

for (const width of [390, 768, 1440]) {
  test(`landing search is aligned and submits once at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');
    await expect(page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Find a complex', exact: true })).toHaveCount(0);
    expect((await page.locator('header').boundingBox()).height).toBeLessThanOrEqual(85);
    const input = page.getByRole('textbox', { name: 'Search estates by name or location', exact: true });
    const form = page.locator('form').filter({ has: input });
    await expect(form.getByText('Find a complex', { exact: true })).toHaveCount(0);
    const submit = form.getByRole('button', { name: 'Search complexes', exact: true });
    await expect(submit).toHaveText('Search');
    const bounds = await form.boundingBox();
    const field = await input.boundingBox();
    const action = await submit.boundingBox();
    expect(field.x + field.width).toBeLessThanOrEqual(action.x);
    expect(action.x + action.width).toBeLessThanOrEqual(bounds.x + bounds.width);
    expect(Math.abs((field.y + field.height / 2) - (action.y + action.height / 2))).toBeLessThanOrEqual(2);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await input.fill('Musgrave Durban');
    await input.press('Enter');
    await expect(page).toHaveURL(/\/estates\?q=Musgrave%20Durban$/);
    await page.goto('/');
    await submit.click();
    await expect(page).toHaveURL(/\/estates$/);
  });
}
