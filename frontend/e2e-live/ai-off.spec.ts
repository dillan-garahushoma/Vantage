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
 * switched off: the brief falls back to the deterministic summary and says so
 * quietly, the triage panel says suggestions are unavailable, and the rest of
 * the estate data is unaffected.
 */
test('the brief falls back to the automatic summary with no AI wording and no error', async ({
  page,
}) => {
  const problems = watchForErrors(page)
  await signInToDashboard(page, ADMIN)

  const panel = briefPanel(page)
  await expect(panel.getByText(/as at/i)).toBeVisible({ timeout: 45_000 })

  // Asking for a brief while the layer is off answers with the deterministic
  // summary and the quiet note — never an error, and never a reason code.
  await panel.getByRole('button', { name: 'Generate AI summary' }).click()
  await expect(panel.getByText('Automatic summary')).toBeVisible({ timeout: 60_000 })
  await expect(panel.getByText(/showing the automatic summary/i)).toBeVisible({ timeout: 60_000 })
  await expect(panel.getByText(/written by ai/i)).toHaveCount(0)
  await expect(panel.getByText(/could not|rejected|failed/i)).toHaveCount(0)
  await expect(panel.getByText(/provider_error|timeout|budget|AI_UNAVAILABLE/)).toHaveCount(0)

  // The deterministic summary is still a real summary with real figures.
  await panel.getByRole('button', { name: /show the figures/i }).click()
  await expect(panel.getByRole('table')).toBeVisible()

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
    await expect(dialog.getByText('Suggestions are not available right now.')).toBeVisible({
      timeout: 60_000,
    })
    await expect(dialog.getByText(/AI_UNAVAILABLE|provider_error/)).toHaveCount(0)
  }

  expect(problems).toEqual([])
})

test('a resident can still read the estate without the AI layer', async ({ page }) => {
  const problems = watchForErrors(page)
  await signInToDashboard(page, RESIDENT)

  await expect(briefPanel(page).getByText(/as at/i)).toBeVisible({ timeout: 45_000 })
  await expect(page.getByText(/suggest triage/i)).toHaveCount(0)

  expect(problems).toEqual([])
})
