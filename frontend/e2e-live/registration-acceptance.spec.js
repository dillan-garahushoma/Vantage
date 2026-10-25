/** Real forms and API writes, for an isolated local test database only. */
import { randomUUID } from 'node:crypto';
import { expect, test } from '@playwright/test';

test('registration paths validate, create accounts, preserve estate selection and submit applications', async ({ page, browser, baseURL }, testInfo) => {
  test.setTimeout(150000);
  page.setDefaultTimeout(15000);
  expect(new URL(baseURL).hostname).toMatch(/^(127\.0\.0\.1|localhost)$/);
  const stamp = `${Date.now()}-${testInfo.project.name}`;
  const password = randomUUID();
  const estateName = `Registration QA Musgrave ${stamp}`;
  const residentEmail = `resident-${stamp}@example.com`;
  const providerEmail = `provider-${stamp}@example.com`;
  const contexts = [];
  async function visitor() {
    const context = await browser.newContext({ baseURL, viewport: page.viewportSize() });
    context.setDefaultTimeout(15000);
    contexts.push(context);
    return context.newPage();
  }
  try {
    // HOA signup uses its dedicated estate-registration endpoint.
    await page.goto('/register');
    await page.getByRole('radio', { name: 'HOA / estate manager', exact: true }).check();
    await page.getByRole('button', { name: 'Create estate and HOA account' }).click();
    await expect(page.getByText('Enter your full name.', { exact: true })).toBeVisible();
    await page.getByLabel('Your full name', { exact: true }).fill('QA Estate Manager');
    await page.getByLabel('Email address', { exact: true }).fill(`hoa-${stamp}@example.com`);
    await page.getByLabel('Password', { exact: true }).fill(password);
    await page.getByLabel('Estate name', { exact: true }).fill(estateName);
    await page.getByLabel('Suburb', { exact: true }).fill('Musgrave');
    await page.getByLabel('City', { exact: true }).fill('Durban');
    await page.getByRole('combobox', { name: /^Province/ }).selectOption('KwaZulu-Natal');
    await page.getByRole('button', { name: 'Create estate and HOA account' }).click();
    await expect(page).toHaveURL(/\/(welcome|admin\/setup)$/);
    await page.goto('/register');
    await expect(page.getByText(/already signed in/i)).toBeVisible();
    await page.getByRole('button', { name: 'Continue to VALORA' }).click();
    await page.goto('/admin/setup');
    await page.getByRole('checkbox', { name: /List this estate in the public directory/ }).click();
    await expect(page.getByRole('checkbox', { name: /List this estate in the public directory/ })).toBeChecked();

    const resident = await visitor();
    await resident.goto('/register');
    await resident.getByRole('button', { name: 'Create resident account' }).click();
    await expect(resident.getByText('Enter your full name.', { exact: true })).toBeVisible();
    await expect(resident.getByText('Enter a valid email address.', { exact: true })).toBeVisible();
    await expect(resident.getByText('Use at least 8 characters.', { exact: true })).toBeVisible();
    await resident.getByLabel('Full name', { exact: true }).fill('QA Resident');
    await resident.getByLabel('Email address', { exact: true }).fill(residentEmail);
    await resident.getByLabel('Password', { exact: true }).fill(password);
    const search = resident.getByRole('textbox', { name: 'Search published complexes' });
    await search.fill(estateName);
    await search.press('Enter');
    await resident.getByRole('button', { name: new RegExp(estateName) }).click();
    await resident.getByRole('button', { name: 'Change', exact: true }).click();
    await expect(search).toBeVisible();
    await resident.getByRole('button', { name: new RegExp(estateName) }).click();
    await resident.getByRole('button', { name: 'Create resident account' }).click();
    await expect(resident).toHaveURL(/\/request-access$/);
    await expect(resident.getByText(estateName, { exact: true })).toBeVisible();
    await resident.getByLabel('Note to the estate office (optional)', { exact: true }).fill('Synthetic local acceptance request.');
    await resident.getByRole('button', { name: 'Send request for approval' }).click();
    await expect(resident.getByText(new RegExp(`Request sent to ${estateName}`, 'i'))).toBeVisible();

    const duplicate = await visitor();
    await duplicate.goto('/register');
    await duplicate.getByLabel('Full name', { exact: true }).fill('QA Duplicate');
    await duplicate.getByLabel('Email address', { exact: true }).fill(residentEmail);
    await duplicate.getByLabel('Password', { exact: true }).fill(password);
    await duplicate.getByRole('button', { name: 'Create resident account' }).click();
    await expect(duplicate.getByText(/account with this email already exists/i)).toBeVisible();
    await expect(duplicate.getByLabel('Email address', { exact: true })).toHaveValue(residentEmail);

    const provider = await visitor();
    await provider.goto('/register');
    await provider.getByRole('radio', { name: 'Service provider', exact: true }).check();
    await provider.getByRole('link', { name: 'Apply to work at an estate' }).click();
    await expect(provider).toHaveURL(/\/provider\/apply$/);
    const estateSelect = provider.getByRole('combobox', { name: /^Estate/ });
    const option = estateSelect.locator('option').filter({ hasText: estateName });
    await option.waitFor({ state: 'attached' });
    await estateSelect.selectOption(await option.getAttribute('value'));
    await provider.getByLabel('Full name', { exact: true }).fill('QA Service Provider');
    await provider.getByLabel('Email address', { exact: true }).fill(providerEmail);
    await provider.getByLabel('Trade', { exact: true }).fill('Plumbing');
    await provider.getByLabel('Phone', { exact: true }).fill('0820000000');
    await provider.getByRole('button', { name: 'Submit application' }).click();
    await expect(provider.getByRole('heading', { name: 'Application sent' })).toBeVisible();
    await expect(provider.getByRole('status')).toContainText('No account has been created yet');
    await page.goto('/admin/members');
    await expect(page.getByText(providerEmail, { exact: false })).toBeVisible();
    await page.goto('/register');
    await page.getByRole('button', { name: 'Sign out and use another account' }).click();
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByLabel('Email address', { exact: true })).toBeVisible();
  } finally {
    for (const context of contexts) await context.close();
  }
});
