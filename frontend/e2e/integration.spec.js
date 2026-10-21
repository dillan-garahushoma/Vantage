import { test, expect } from '@playwright/test';
test.beforeEach(async ({ page }) => {
    // A local installation must remain usable with offline font fallbacks.
    await page.route(/https:\/\/fonts\.(googleapis|gstatic)\.com\//, (route) => route.abort());
});
test('contact records a message through the API and fits a narrow viewport', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    let submitted;
    await page.route('**/api/v1/contact', async (route) => {
        if (route.request().method() === 'OPTIONS') {
            await route.fulfill({ status: 204, headers: { 'access-control-allow-origin': '*', 'access-control-allow-methods': 'POST, OPTIONS', 'access-control-allow-headers': '*' } });
            return;
        }
        submitted = route.request().postDataJSON();
        await route.fulfill({ status: 201, contentType: 'application/json', headers: { 'access-control-allow-origin': '*' }, body: JSON.stringify({ id: 1 }) });
    });
    await page.goto('/contact', { waitUntil: 'domcontentloaded' });
    await page.getByLabel('Your name').fill('Test Resident');
    await page.getByLabel('Email address').fill('resident@example.com');
    await page.getByLabel('Message', { exact: true }).fill('Please help with onboarding our estate.');
    await page.getByRole('button', { name: 'Send message' }).click();
    await expect(page.getByRole('status')).toContainText('Message received');
    expect(submitted?.message).toBe('Please help with onboarding our estate.');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: '../../review-evidence/integrated-contact-mobile.png', fullPage: true });
});
test('a failed contact request preserves the message and never reports success', async ({ page }) => {
    await page.route('**/api/v1/contact', async (route) => {
        await route.fulfill({ status: route.request().method() === 'OPTIONS' ? 204 : 503, contentType: 'application/json', headers: { 'access-control-allow-origin': '*', 'access-control-allow-methods': 'POST, OPTIONS', 'access-control-allow-headers': '*' }, body: route.request().method() === 'OPTIONS' ? '' : JSON.stringify({ detail: 'Service unavailable' }) });
    });
    await page.goto('/contact', { waitUntil: 'domcontentloaded' });
    await page.getByLabel('Your name').fill('Test Resident');
    await page.getByLabel('Email address').fill('resident@example.com');
    await page.getByLabel('Message', { exact: true }).fill('Please keep this message if the API fails.');
    await page.getByRole('button', { name: 'Send message' }).click();
    await expect(page.getByRole('alert')).toContainText('Service unavailable');
    await expect(page.getByLabel('Message', { exact: true })).toHaveValue('Please keep this message if the API fails.');
    await expect(page.getByText('Message received. Your enquiry has been recorded.')).toHaveCount(0);
});
