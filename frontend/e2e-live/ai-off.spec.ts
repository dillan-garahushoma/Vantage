import { expect, test } from '@playwright/test'

import {
  ADMIN,
  RESIDENT,
  briefPanel,
  openTriableComplaint,
  signInToDashboard,
  watchForErrors,
} from './helpers'

/**
 * AI OFF (`AI_ENABLED=false`) — the product must work anyway.
 *
 * Nothing on these screens may turn into an error just because the AI layer is
 * switched off: no simulated prose is presented as an AI result, the triage
 * panel says that no triage was generated, and the rest of the estate data is
 * unaffected.
 */
test('the brief makes unavailable AI explicit and never displays a simulated summary', async ({
  page,
}) => {
  const problems = watchForErrors(page)
  await signInToDashboard(page, ADMIN)

  const panel = briefPanel(page)
  await expect(panel.getByRole('heading', { name: 'Estate health brief' })).toBeVisible({ timeout: 45_000 })

  // Asking while the layer is off never substitutes a deterministic template
  // for a requested AI result.
  await panel.getByRole('button', { name: 'Generate AI summary' }).click()
  await expect(panel.getByText('AI summary unavailable')).toBeVisible({ timeout: 60_000 })
  await expect(panel.getByText(/No AI summary was created/i)).toBeVisible({ timeout: 60_000 })
  await expect(panel.getByText(/written by ai/i)).toHaveCount(0)
  await expect(panel.getByText(/automatic summary/i)).toHaveCount(0)
  await expect(panel.getByText(/could not|rejected|failed/i)).toHaveCount(0)
  await expect(panel.getByText(/provider_error|timeout|budget|AI_UNAVAILABLE/)).toHaveCount(0)

  expect(problems).toEqual([])
})

test('the triage panel says suggestions are unavailable, without a reason code', async ({ page }) => {
  const problems = watchForErrors(page)
  await signInToDashboard(page, ADMIN)

  await page.goto('/app/complaints')
  const rows = page.locator('tbody tr')
  await expect(rows.first()).toBeVisible({ timeout: 45_000 })

  // The shared helper walks the register and skips the complaints the API would
  // refuse, so this test asks about a suggestion exactly where one is possible.
  const dialog = await openTriableComplaint(page)
  const suggest = dialog.getByRole('button', { name: /suggest triage/i })
  await expect(suggest.or(dialog.getByText(/Suggestion accepted as-is|Decided labels:/))).toBeVisible({
    timeout: 45_000,
  })
  if (await suggest.isVisible()) {
    await suggest.click()
    await expect(dialog.getByText(/AI triage is unavailable right now/)).toBeVisible({
      timeout: 60_000,
    })
    await expect(dialog.getByText(/AI_UNAVAILABLE|provider_error/)).toHaveCount(0)
  }

  expect(problems).toEqual([])
})

test('a resident can still read the estate without the AI layer', async ({ page }) => {
  const problems = watchForErrors(page)
  await signInToDashboard(page, RESIDENT)

  await expect(briefPanel(page).getByRole('heading', { name: 'Estate health brief' })).toBeVisible({ timeout: 45_000 })
  await expect(page.getByText(/suggest triage/i)).toHaveCount(0)

  expect(problems).toEqual([])
})
