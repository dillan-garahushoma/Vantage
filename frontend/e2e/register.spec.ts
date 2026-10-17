import { expect, test, type Page } from '@playwright/test'

/**
 * Registration's account-type picker, in a real browser.
 *
 * Vitest covers the behaviour; this covers what jsdom cannot: that the card
 * really is one click target once CSS is applied, that a click anywhere inside
 * its border selects it — including the description, which is the part that
 * explains the choice and therefore the part people click — and that the
 * selection is visible without relying on colour alone.
 */
test.describe('the account-type picker', () => {
  /**
   * The card a choice lives on, reached from the radio it contains — the card is
   * a `<label>`, so the two are the same control and no test hook is needed.
   */
  const card = (page: Page, accountType: string) =>
    page.locator('label').filter({ has: page.getByRole('radio', { name: accountType }) })

  test.beforeEach(async ({ page }) => {
    // The webfonts come from a CDN: abort them so navigation is deterministic
    // and the spec runs offline, as the other e2e specs do.
    await page.route('https://fonts.googleapis.com/**', (route) => route.abort())
    await page.route('https://fonts.gstatic.com/**', (route) => route.abort())
  })

  test('the description and the card body both choose the account type', async ({ page }) => {
    await page.goto('/register')

    const heading = page.getByRole('heading', { name: /account$/ })

    // The description of the provider card.
    await page.getByText('Do the work.').click()
    await expect(page.getByRole('heading', { name: 'Service provider account' })).toBeVisible()
    await expect(page.getByLabel(/^trade/i)).toBeVisible()

    // The empty space inside the administrator card, away from its text.
    const adminCard = card(page, 'Estate administrator')
    const box = (await adminCard.boundingBox())!
    await adminCard.click({ position: { x: box.width - 12, y: box.height - 10 } })
    await expect(page.getByRole('heading', { name: 'Estate administrator account' })).toBeVisible()
    await expect(page.getByLabel(/estate name/i)).toBeVisible()

    await expect(heading).toBeVisible()
  })

  test('the chosen card is marked by more than colour alone', async ({ page }) => {
    await page.goto('/register')

    const resident = card(page, 'Resident')
    const provider = card(page, 'Service provider')

    // The radio state is the accessible signal; it must agree with the styling.
    await expect(page.getByRole('radio', { name: 'Resident' })).toBeChecked()
    await expect(page.getByRole('radio', { name: 'Service provider' })).not.toBeChecked()

    const [chosen, other] = await Promise.all([
      resident.evaluate((el) => getComputedStyle(el).borderColor),
      provider.evaluate((el) => getComputedStyle(el).borderColor),
    ])
    expect(chosen).not.toBe(other)
  })

  test('keyboard reaches the choice and rings the whole card, not just the dot', async ({ page }) => {
    await page.goto('/register')

    // Tab from a cold load, so the focus genuinely comes from the keyboard —
    // which is what `:focus-visible` responds to, and what a person pressing Tab
    // actually does.
    const resident = page.getByRole('radio', { name: 'Resident' })
    for (let press = 0; press < 12; press += 1) {
      if (await resident.evaluate((el) => el === document.activeElement)) break
      await page.keyboard.press('Tab')
    }
    await expect(resident).toBeFocused()

    const ring = (accountType: string) =>
      card(page, accountType).evaluate((el) => {
        const style = getComputedStyle(el)
        return `${style.outlineStyle} ${style.outlineWidth} ${style.outlineColor}`
      })

    // The 16px dot is easy to miss; the card the choice belongs to is not.
    expect(await ring('Resident')).toBe('dotted 2px rgb(31, 111, 92)')

    await page.keyboard.press('ArrowDown')
    await expect(page.getByRole('radio', { name: 'Estate administrator' })).toBeChecked()
    expect(await ring('Estate administrator')).toBe('dotted 2px rgb(31, 111, 92)')
    // And only one card wears it. `outline-style: none` is the whole test: an
    // unfocused card still reports a default width, just nothing painted.
    expect(await ring('Resident')).toContain('none ')
  })

  test('a rejected registration is a notice whose signal bar is painted', async ({ page }) => {
    await page.route('**/api/v1/auth/register', (route) =>
      route.fulfill({
        status: 409,
        json: { detail: 'An account with that email already exists.' },
      }),
    )

    await page.goto('/register')
    await page.getByLabel(/full name/i).fill('Thandi Nkosi')
    await page.getByLabel(/email address/i).fill('thandi@example.co.za')
    await page.getByLabel(/^password/i).fill('aGoodPassword1')
    await page.getByRole('button', { name: /create account/i }).click()

    await expect(page.getByText('An account with that email already exists.')).toBeVisible()

    // The notice carries a 2px signal bar over a hairline border — a utility
    // overriding a `.hairline`. While `.hairline` sat in the utilities layer it
    // won that fight, so the bar stayed 1px grey on every notice in the product.
    const border = await page.locator('div.border-l-2').first().evaluate((el) => {
      const style = getComputedStyle(el)
      return { width: style.borderLeftWidth, color: style.borderLeftColor }
    })
    expect(border.width).toBe('2px')
    expect(border.color).toBe('rgb(228, 87, 46)')
  })

  test('stays inside a 390px viewport', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/register')

    await page.getByText('Do the work.').click()
    await expect(page.getByRole('heading', { name: 'Service provider account' })).toBeVisible()

    const widths = await page.evaluate(() => ({
      scroll: document.documentElement.scrollWidth,
      client: document.documentElement.clientWidth,
    }))
    expect(widths.scroll).toBeLessThanOrEqual(widths.client)
  })
})
