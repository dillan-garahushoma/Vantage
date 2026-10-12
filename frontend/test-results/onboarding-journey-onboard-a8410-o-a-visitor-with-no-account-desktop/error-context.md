# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onboarding-journey.spec.ts >> onboarding journey >> the published estate is visible to a visitor with no account
- Location: e2e-live\onboarding-journey.spec.ts:201:3

# Error details

```
Error: page.goto: net::ERR_EMPTY_RESPONSE at http://localhost:4173/estates
Call log:
  - navigating to "http://localhost:4173/estates", waiting until "load"

```

# Test source

```ts
  106 |   await page.getByLabel('Description (optional)').fill(ESTATE.description)
  107 |   await page.getByRole('button', { name: /create account and register the estate/i }).click()
  108 | }
  109 | 
  110 | async function registerResident(page: Page) {
  111 |   await page.goto('/register')
  112 |   await page.getByRole('radio', { name: 'Resident', exact: true }).check()
  113 |   await page.getByLabel('Full name').fill(RESIDENT.name)
  114 |   await page.getByLabel('Email address').fill(RESIDENT.email)
  115 |   await page.getByLabel('Password').fill(PASSWORD)
  116 |   await page.getByRole('button', { name: /create account$/i }).click()
  117 | }
  118 | 
  119 | async function registerProvider(page: Page) {
  120 |   await page.goto('/register')
  121 |   await page.getByRole('radio', { name: 'Service provider', exact: true }).check()
  122 |   await page.getByLabel('Full name').fill(PROVIDER.name)
  123 |   await page.getByLabel('Email address').fill(PROVIDER.email)
  124 |   await page.getByLabel('Password').fill(PASSWORD)
  125 |   await page.getByLabel('Trade').fill('plumbing')
  126 |   await page.getByLabel('Contact phone').fill('082 000 0000')
  127 |   await page.getByRole('button', { name: /create account$/i }).click()
  128 | }
  129 | 
  130 | /** The estate's one live join code, as the setup screen shows it. */
  131 | async function readJoinCode(page: Page): Promise<string> {
  132 |   const card = page.locator('section', { has: page.getByRole('heading', { name: 'Join code' }) })
  133 |   const code = (await card.locator('p.num').first().textContent())?.trim() ?? ''
  134 |   expect(code, 'the setup screen must show one live join code').toMatch(/^[A-Z0-9]{10}$/)
  135 |   return code
  136 | }
  137 | 
  138 | test.describe('onboarding journey', () => {
  139 |   test('an estate administrator can register the estate and finish the checklist', async ({
  140 |     page,
  141 |   }) => {
  142 |     const problems: string[] = []
  143 |     page.on('pageerror', (error) => problems.push(`pageerror: ${error.message}`))
  144 | 
  145 |     await registerEstateAdmin(page)
  146 | 
  147 |     // /welcome resolves the destination from membership: an administrator of a
  148 |     // brand-new estate belongs on the setup checklist.
  149 |     await expect(page).toHaveURL(/\/admin\/setup/, { timeout: 30_000 })
  150 |     await expect(page.getByRole('heading', { level: 1 })).toContainText(ESTATE.name)
  151 |     // One of five: the description travelled with the registration itself.
  152 |     await expect(page.getByText('1 of 5', { exact: false })).toBeVisible()
  153 |     await expect(page.getByText('Describe the estate')).toBeVisible()
  154 | 
  155 |     // 1. The description. Field labels carry their hint inside the same label, so
  156 |     //    these are anchored matches on the control's role and name.
  157 |     await page.getByRole('textbox', { name: /^Description/ }).fill(ESTATE.description)
  158 |     await page.getByRole('button', { name: 'Save description' }).click()
  159 |     await expect(page.getByText('Saved.')).toBeVisible()
  160 | 
  161 |     // 2. Units, pasted as a list.
  162 |     await page
  163 |       .getByRole('textbox', { name: /^Units/ })
  164 |       .fill(`${UNIT_A}, 12 Ridge Close, 96, 3, 2\n${UNIT_B}, 14 Ridge Close, 88, 2, 2`)
  165 |     await page.getByRole('button', { name: 'Add units' }).click()
  166 |     await expect(page.getByText('Added 2 units.')).toBeVisible()
  167 | 
  168 |     // 3. A join code, which is what a resident will redeem.
  169 |     await page.getByRole('button', { name: /issue a code/i }).click()
  170 |     const code = await readJoinCode(page)
  171 |     expect(code).toHaveLength(10)
  172 | 
  173 |     // 4. A photograph, uploaded the way an administrator would: the file input is
  174 |     //    visually hidden behind the drop zone, and the caption is set first.
  175 |     await page.getByRole('textbox', { name: /^Caption/ }).fill('The pool at dusk')
  176 |     await page
  177 |       .getByLabel('Choose a photograph to upload')
  178 |       .setInputFiles('e2e-live/fixtures/pool.jpg')
  179 |     await expect(page.getByText('1 of 12 uploaded')).toBeVisible({ timeout: 30_000 })
  180 |     await expect(page.getByText('The pool at dusk')).toBeVisible()
  181 | 
  182 |     // 5. Publishing, which is what makes the estate findable at all. These are
  183 |     //    controlled checkboxes that follow the server's answer, so the box moves
  184 |     //    when the PATCH lands rather than on the click — hence `click()` and a
  185 |     //    polled assertion instead of `check()`.
  186 |     await page.getByLabel(/list this estate in the public directory/i).click()
  187 |     await expect(page.getByLabel(/list this estate in the public directory/i)).toBeChecked({
  188 |       timeout: 30_000,
  189 |     })
  190 | 
  191 |     // The checklist now reports all five steps done, from the API's own values.
  192 |     await expect(page.getByText('5 of 5', { exact: false })).toBeVisible({ timeout: 30_000 })
  193 | 
  194 |     // The join code survives a reload: it is the estate's, not the screen's state.
  195 |     await page.reload()
  196 |     expect(await readJoinCode(page)).toBe(code)
  197 | 
  198 |     expect(problems).toEqual([])
  199 |   })
  200 | 
  201 |   test('the published estate is visible to a visitor with no account', async ({ page }) => {
  202 |     const problems: string[] = []
  203 |     page.on('pageerror', (error) => problems.push(`pageerror: ${error.message}`))
  204 | 
  205 |     // No session at all: this is the unauthenticated directory.
> 206 |     await page.goto('/estates')
      |                ^ Error: page.goto: net::ERR_EMPTY_RESPONSE at http://localhost:4173/estates
  207 |     await page.getByLabel(/search by name, suburb or city/i).fill(ESTATE.name)
  208 |     await page.getByRole('button', { name: 'Search' }).click()
  209 | 
  210 |     const card = page.locator('li', { hasText: ESTATE.name }).first()
  211 |     await expect(card).toBeVisible({ timeout: 30_000 })
  212 |     await expect(card.getByText(/2 units/)).toBeVisible()
  213 | 
  214 |     await card.getByRole('link', { name: /view this complex/i }).click()
  215 |     await expect(page.getByRole('heading', { level: 1, name: ESTATE.name })).toBeVisible()
  216 |     await expect(page.getByText(ESTATE.description)).toBeVisible()
  217 |     // The score is a separate decision and this estate never published one.
  218 |     await expect(page.getByText('Living Score')).toHaveCount(0)
  219 |     // And nothing about the units, residents or complaints is published.
  220 |     await expect(page.getByText(UNIT_A)).toHaveCount(0)
  221 |     await expect(page.getByText(UNIT_B)).toHaveCount(0)
  222 | 
  223 |     expect(problems).toEqual([])
  224 |   })
  225 | 
  226 |   test('a resident joins with the code, and their complaint is recorded', async ({ page }) => {
  227 |     const problems: string[] = []
  228 |     page.on('pageerror', (error) => problems.push(`pageerror: ${error.message}`))
  229 | 
  230 |     await registerResident(page)
  231 |     // A new resident has no estate, so role routing sends them to redeem a code.
  232 |     await expect(page).toHaveURL(/\/join/, { timeout: 30_000 })
  233 | 
  234 |     // The administrator reads the live code; a resident never sees it until a code
  235 |     // is handed to them.
  236 |     await signInAsAdmin(page)
  237 |     const code = await readJoinCode(page)
  238 | 
  239 |     await signOut(page)
  240 |     await signIn(page, RESIDENT.email)
  241 |     await expect(page).toHaveURL(/\/join/, { timeout: 30_000 })
  242 |     await page.getByRole('textbox', { name: /^Join code/ }).fill(code)
  243 |     await page.getByRole('textbox', { name: /^Unit number/ }).fill(UNIT_A)
  244 |     await page.getByRole('button', { name: /join the estate/i }).click()
  245 | 
  246 |     await expect(page).toHaveURL(/\/app$/, { timeout: 30_000 })
  247 |     await expect(page.getByRole('option', { name: ESTATE.name })).toHaveCount(1)
  248 | 
  249 |     // The resident logs a complaint against their unit.
  250 |     await page.goto('/app/complaints')
  251 |     // Two of these exist on a resident's complaints screen (the header and the
  252 |     // empty-state action) and they open the same drawer.
  253 |     await page.getByRole('button', { name: 'Log a complaint' }).first().click()
  254 |     const dialog = page.getByRole('dialog')
  255 |     await expect(dialog).toBeVisible()
  256 |     // The estate holds exactly the two units this journey registered, so the first
  257 |     // real option (index 0 is “Select a unit…”) is the resident's own.
  258 |     await dialog.getByLabel('Which unit?').selectOption({ index: 1 })
  259 |     await dialog.getByLabel('Category').selectOption('water')
  260 |     await dialog.getByLabel('Priority').selectOption('high')
  261 |     await dialog
  262 |       .getByLabel('What is wrong?')
  263 |       .fill('Sewage overflow at the Block C boundary — pooling near the pedestrian gate.')
  264 |     await dialog.getByRole('button', { name: 'Log complaint' }).click()
  265 | 
  266 |     await expect(dialog).toBeHidden({ timeout: 30_000 })
  267 |     const row = page.locator('tbody tr', { hasText: /sewage overflow/i }).first()
  268 |     await expect(row).toBeVisible()
  269 |     await expect(row.getByText('Logged')).toBeVisible()
  270 | 
  271 |     expect(problems).toEqual([])
  272 |   })
  273 | 
  274 |   test('a provider waits to be added, and the administrator adds them by email', async ({
  275 |     page,
  276 |   }) => {
  277 |     const problems: string[] = []
  278 |     page.on('pageerror', (error) => problems.push(`pageerror: ${error.message}`))
  279 | 
  280 |     await registerProvider(page)
  281 |     // A provider cannot add themselves to an estate: the screen says so.
  282 |     await expect(page).toHaveURL(/\/provider\/waiting/, { timeout: 30_000 })
  283 |     await expect(
  284 |       page.getByRole('heading', { name: /waiting to be added to an estate/i }),
  285 |     ).toBeVisible()
  286 |     await expect(page.getByText(/Plumbing/)).toBeVisible()
  287 | 
  288 |     await signInAsAdmin(page)
  289 |     await page.goto('/admin/members')
  290 |     await expect(page.getByText(RESIDENT.name)).toBeVisible({ timeout: 30_000 })
  291 | 
  292 |     await page.getByRole('textbox', { name: /^Provider email/ }).fill(PROVIDER.email)
  293 |     await page.getByRole('button', { name: /add provider/i }).click()
  294 |     await expect(page.getByText(/can now be assigned work in this estate/i)).toBeVisible({
  295 |       timeout: 30_000,
  296 |     })
  297 |     await expect(page.locator('tbody tr', { hasText: PROVIDER.name })).toContainText(
  298 |       'Service provider',
  299 |     )
  300 | 
  301 |     // The provider now has an estate, and no work yet — which the screen says plainly.
  302 |     await signOut(page)
  303 |     await signIn(page, PROVIDER.email)
  304 |     await expect(page).toHaveURL(/\/app$/, { timeout: 30_000 })
  305 |     await page.goto('/provider/work')
  306 |     await expect(page.getByText('Nothing assigned to you yet')).toBeVisible({ timeout: 30_000 })
```