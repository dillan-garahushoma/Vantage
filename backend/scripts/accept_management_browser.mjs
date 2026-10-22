import { chromium } from '../../frontend/node_modules/playwright/index.mjs';

const browser = await chromium.launch({ headless: true });
let stage = 'create-page';
try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', () => errors.push('Browser script error'));
    await page.route(/https:\/\/fonts\.(googleapis|gstatic)\.com\//, route => route.abort());
    stage = 'login-page';
    await page.goto(process.env.VALORA_ACCEPTANCE_UI + '/login');
    await page.locator('input[name="email"]').fill(process.env.VALORA_ACCEPTANCE_EMAIL);
    await page.locator('input[name="password"]').fill(process.env.VALORA_ACCEPTANCE_PASSWORD);
    stage = 'submit-login';
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    stage = 'signed-in-navigation';
    await page.waitForURL(/\/app(?:\?.*)?$/);
    stage = 'complaint-record';
    await page.goto(process.env.VALORA_ACCEPTANCE_UI + '/app/complaints');
    await page.getByText('Fictional leaking kitchen tap', { exact: false }).first().waitFor();
    if (errors.length) throw new Error('Live browser emitted errors');
} catch {
    process.stdout.write(JSON.stringify({ failed_stage: stage }));
    process.exitCode = 1;
} finally {
    await browser.close();
}
