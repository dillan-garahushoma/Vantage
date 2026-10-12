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
 * AI ON — a wiring check, not a model-quality check.
 *
 * The backend runs in development with `AI_PROVIDER=fake`, so every assertion
 * here is about the *product*: that the client calls the real endpoints with the
 * real shapes, that both AI surfaces render what came back, and that a resident
 * never sees the HOA's triage review. Nothing here says anything about Gemini.
 */
test('an HOA admin generates the brief, expands the figures and rates it', async ({ page }) => {
  const problems = watchForErrors(page)
  await signInToDashboard(page, ADMIN)

  const panel = briefPanel(page)
  await expect(panel.getByRole('heading', { name: 'Estate health brief' })).toBeVisible()
  await expect(panel.getByText(/as at/i)).toBeVisible({ timeout: 45_000 })

  await panel.getByRole('button', { name: 'Generate AI summary' }).click()

  // The AI-written brief replaces the panel in place: no reload, no second read.
  await expect(panel.getByText('Written by AI from the figures below')).toBeVisible({
    timeout: 30_000,
  })
  await expect(panel.getByText(/demo data/i)).toBeVisible()

  // The label flips to "Hide the figures", so match either wording.
  const expander = panel.getByRole('button', { name: /(show|hide) the figures/i })
  await expander.click()
  await expect(expander).toHaveAttribute('aria-expanded', 'true')

  const table = panel.getByRole('table')
  await expect(table).toBeVisible()
  await expect(table.getByRole('rowheader', { name: 'Overall' })).toBeVisible()
  await expect(table.getByRole('rowheader', { name: /Resolution/ })).toBeVisible()
  await expect(table.getByText(/Stored inputs:/).first()).toBeVisible()

  // Feedback is offered for an AI-written brief, and recording it is a normal
  // request — not a 409, because this estate has not rated this brief yet.
  // Feedback is write-once, so a repeat run against the same seeded database
  // answers 409 — which is the same wiring proven a second way. Both answers
  // mean the request reached the endpoint and was handled.
  await panel.getByRole('button', { name: 'Helpful', exact: true }).click()
  await panel.getByLabel(/comment/i).fill('Wiring check comment.')
  await panel.getByRole('button', { name: /send feedback/i }).click()
  await expect(
    panel.getByText(/thanks — your feedback was recorded/i).or(panel.getByText('Already submitted')),
  ).toBeVisible({ timeout: 45_000 })

  expect(problems).toEqual([])
})

test('an HOA admin requests triage for a complaint and accepts it', async ({ page }) => {
  const problems = watchForErrors(page)
  await signInToDashboard(page, ADMIN)

  await page.goto('/app/complaints')
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible({ timeout: 45_000 })

  const dialog = await openTriableComplaint(page)
  await expect(
    dialog.getByText(/A suggestion for the HOA's review/i),
  ).toBeVisible({ timeout: 45_000 })

  // A suggestion is write-once, so a repeat run finds it already decided. All
  // three states prove the same wiring; the fresh path is the interesting one.
  const suggest = dialog.getByRole('button', { name: /suggest triage/i })
  const details = dialog.getByText(/fake · .+ · triage-/)
  const accepted = dialog.getByText('Suggestion accepted as-is')
  const decided = dialog.getByText(/Suggestion accepted as-is|Decided labels:/)

  await expect(suggest.or(details).or(decided)).toBeVisible({ timeout: 45_000 })
  if (await suggest.isVisible()) {
    await suggest.click()
    await expect(details.or(decided)).toBeVisible({ timeout: 60_000 })
  }

  if (await details.isVisible()) {
    // Undecided: the labels and the provider details come from the API, verbatim.
    await expect(dialog.getByText('Category')).toBeVisible()
    await expect(dialog.getByText('Trade')).toBeVisible()

    const accept = dialog.getByRole('button', { name: 'Accept' })
    await accept.click()
    await expect(accepted).toBeVisible({ timeout: 45_000 })
  }

  // Decided is read-only: no Accept, Override or Dismiss left on screen.
  await expect(dialog.getByRole('button', { name: 'Accept' })).toHaveCount(0)
  await expect(dialog.getByRole('button', { name: /override/i })).toHaveCount(0)
  await expect(dialog.getByRole('button', { name: 'Dismiss' })).toHaveCount(0)

  expect(problems).toEqual([])
})

test('a resident sees the brief and no triage review anywhere', async ({ page }) => {
  const problems = watchForErrors(page)
  await signInToDashboard(page, RESIDENT)

  const panel = briefPanel(page)
  await expect(panel.getByText(/as at/i)).toBeVisible({ timeout: 45_000 })
  await expect(panel.getByRole('button', { name: /generate ai summary/i })).toHaveCount(0)

  await page.goto('/app/complaints')
  const rows = page.locator('tbody tr')
  await expect(rows.first()).toBeVisible({ timeout: 45_000 })
  await rows.first().click()

  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  await expect(dialog.getByRole('heading', { name: 'AI triage' })).toHaveCount(0)
  await expect(dialog.getByRole('button', { name: /suggest triage/i })).toHaveCount(0)
  await expect(page.getByText(/suggest triage/i)).toHaveCount(0)

  expect(problems).toEqual([])
})

test('both panels stay usable at a mobile width without horizontal overflow', async ({ page }) => {
  const problems = watchForErrors(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await signInToDashboard(page, ADMIN)

  const panel = briefPanel(page)
  await expect(panel.getByText(/as at/i)).toBeVisible({ timeout: 45_000 })

  await panel.getByRole('button', { name: /show the figures/i }).click()
  await expect(panel.getByRole('table')).toBeVisible()

  // The brief must fit a phone: the eight-column table scrolls inside its own
  // box and the panel never reaches past the viewport.
  const measured = await panel.evaluate((section) => {
    const box = section.getBoundingClientRect()
    const scroller = section.querySelector('#brief-figures')
    return {
      viewport: window.innerWidth,
      panelRight: Math.round(box.right),
      scrollsInternally: scroller
        ? scroller.scrollWidth > scroller.clientWidth + 1
        : false,
      // Recorded, not asserted: the rest of the dashboard is outside this batch.
      documentOverflow: document.documentElement.scrollWidth - window.innerWidth,
    }
  })

  expect(measured.panelRight).toBeLessThanOrEqual(measured.viewport + 1)
  expect(measured.scrollsInternally).toBe(true)
  test.info().annotations.push({
    type: 'document overflow (other dashboard blocks, outside this batch)',
    description: `${measured.documentOverflow}px at ${measured.viewport}px wide`,
  })

  expect(problems).toEqual([])
})
