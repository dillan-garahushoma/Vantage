# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onboarding-journey.spec.ts >> onboarding journey >> a provider waits to be added, and the administrator adds them by email
- Location: e2e-live\onboarding-journey.spec.ts:274:3

# Error details

```
Error: page.goto: net::ERR_EMPTY_RESPONSE at http://localhost:4173/register
Call log:
  - navigating to "http://localhost:4173/register", waiting until "load"

```

# Test source

```ts
  20  |  * later ones skip with a clear message if the administrator from the first test is
  21  |  * not there. Run with `E2E_BASE_URL=… npm run test:e2e:live`.
  22  |  */
  23  | const PASSWORD = 'ValoraJourney2026!'
  24  | const stamp = process.env.JOURNEY_STAMP ?? String(Date.now()).slice(-9)
  25  | 
  26  | const ADMIN = { email: `journey-admin-${stamp}@example.co.za`, name: 'Nomvula Dlamini' }
  27  | const RESIDENT = { email: `journey-resident-${stamp}@example.co.za`, name: 'Thandi Nkosi' }
  28  | const PROVIDER = { email: `journey-provider-${stamp}@example.co.za`, name: 'Sipho Mokoena' }
  29  | 
  30  | const ESTATE = {
  31  |   name: `Ridge Close Journey ${stamp}`,
  32  |   suburb: 'Centurion',
  33  |   city: 'Tshwane',
  34  |   province: 'Gauteng',
  35  |   description: 'A 24-unit complex with a shared pool and a single monitored gate.',
  36  | }
  37  | 
  38  | const UNIT_A = 'T-101'
  39  | const UNIT_B = 'T-102'
  40  | 
  41  | /* --------------------------------------------------------------- session */
  42  | 
  43  | /**
  44  |  * Ends the session. The shell's own sign-out button is used when the screen has
  45  |  * one — that is the path a person takes — and localStorage is cleared as well, so
  46  |  * a spec that continues from a screen without the button still starts clean.
  47  |  * (Signing out from an onboarding screen lands on the sign-in page, because that
  48  |  * screen redirects a session-less visitor there; the landing page and the sign-in
  49  |  * page are both fine destinations for the next step.)
  50  |  */
  51  | async function signOut(page: Page) {
  52  |   const button = page.getByRole('button', { name: 'Sign out' })
  53  |   if ((await button.count()) > 0) {
  54  |     await button.first().click()
  55  |     await expect(page).toHaveURL(/\/(login)?$/, { timeout: 20_000 })
  56  |   }
  57  |   await page.evaluate(() => localStorage.clear())
  58  | }
  59  | 
  60  | async function signIn(page: Page, email: string) {
  61  |   // Two navigations on purpose. The app returns you to where you were before it
  62  |   // sent you here (`location.state.from`, set when a protected screen redirects),
  63  |   // and a browser reload of the same URL keeps that history entry's state. An
  64  |   // intermediate page makes the next `/login` a fresh entry with no deep link, so
  65  |   // the sign-in lands wherever the account actually belongs.
  66  |   await page.goto('/estates')
  67  |   await page.goto('/login')
  68  |   await page.getByLabel('Email address').fill(email)
  69  |   await page.getByLabel('Password').fill(PASSWORD)
  70  |   await page.getByRole('button', { name: 'Sign in' }).click()
  71  | }
  72  | 
  73  | /**
  74  |  * Signs in as the administrator this run created, and skips the test — rather
  75  |  * than failing after two minutes of waiting — when that account is not there.
  76  |  */
  77  | async function signInAsAdmin(page: Page) {
  78  |   await signOut(page)
  79  |   await signIn(page, ADMIN.email)
  80  | 
  81  |   const arrived = await page
  82  |     .waitForURL(/\/(welcome|admin\/setup|app|join|provider\/waiting)$/, { timeout: 30_000 })
  83  |     .then(() => true)
  84  |     .catch(() => false)
  85  | 
  86  |   if (!arrived && (await page.getByText(/invalid email or password/i).count()) > 0) {
  87  |     test.skip(
  88  |       true,
  89  |       `no administrator for stamp ${stamp}: run the whole file in order, or let the first test create it`,
  90  |     )
  91  |   }
  92  |   await expect(page).toHaveURL(/\/admin\/setup/, { timeout: 30_000 })
  93  | }
  94  | 
  95  | /** Registers an estate administrator and the estate in one step. */
  96  | async function registerEstateAdmin(page: Page) {
  97  |   await page.goto('/register')
  98  |   await page.getByRole('radio', { name: 'Estate administrator', exact: true }).check()
  99  |   await page.getByLabel('Full name').fill(ADMIN.name)
  100 |   await page.getByLabel('Email address').fill(ADMIN.email)
  101 |   await page.getByLabel('Password').fill(PASSWORD)
  102 |   await page.getByLabel('Estate name').fill(ESTATE.name)
  103 |   await page.getByLabel('Suburb').fill(ESTATE.suburb)
  104 |   await page.getByLabel('City').fill(ESTATE.city)
  105 |   await page.getByLabel('Province').selectOption(ESTATE.province)
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
> 120 |   await page.goto('/register')
      |              ^ Error: page.goto: net::ERR_EMPTY_RESPONSE at http://localhost:4173/register
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
  206 |     await page.goto('/estates')
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
```