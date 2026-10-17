import { expect, test, type Page } from '@playwright/test'

/**
 * Resident approvals, exercised for real in a browser at desktop width.
 *
 * The API is mocked so the flow can run without a database, but everything else is
 * the real app: the resident picks a complex from the directory, submits, and the
 * administrator confirms and decides from the queue. Each decision is asserted by
 * the request the app actually sent, so a screen that only *looks* right fails.
 */
const DESKTOP = { width: 1280, height: 900 }

const ESTATE = {
  estate_id: 1,
  estate_name: 'Ridge Close Estate',
  suburb: 'Centurion',
  city: 'Tshwane',
  province: 'Gauteng',
  membership_roles: ['resident', 'hoa_admin'],
  property_ids: [10],
  is_estate_admin: true,
  is_estate_provider: false,
}

const ADMIN_USER = {
  id: 3,
  email: 'admin@example.co.za',
  full_name: 'Nomvula Dlamini',
  role: 'hoa_admin',
  unit_no: 'A-1',
  email_verified: true,
  hoa_approved: true,
}

const RESIDENT_USER = { ...ADMIN_USER, id: 8, full_name: 'Thandi Nkosi', role: 'resident' }

const PUBLIC_ESTATES = {
  items: [
    {
      estate_id: 4,
      name: 'Zambezi Country Estate',
      suburb: 'Montana',
      city: 'Pretoria',
      province: 'Gauteng',
      description: null,
      unit_count: 24,
      cover_photo_public_id: null,
    },
  ],
  total: 1,
  page: 1,
  size: 8,
  pages: 1,
}

const PENDING_REQUEST = {
  request_id: 31,
  estate_id: 1,
  estate_name: 'Ridge Close Estate',
  unit_no: 'A-101',
  status: 'pending',
  applicant_name: 'Thandi Nkosi',
  applicant_email: 'thandi@example.co.za',
  applicant_phone: '082 000 0000',
  note: 'Lease starts 1 Nov',
  created_at: '2026-10-13T09:30:00Z',
  decided_at: null,
  decision_note: null,
}

interface Call {
  method: string
  pathname: string
  body: string | null
}

async function withMocks(
  page: Page,
  options: { user: typeof ADMIN_USER; posts?: Record<string, unknown> },
): Promise<Call[]> {
  const calls: Call[] = []

  await page.route('https://fonts.googleapis.com/**', (route) => route.abort())
  await page.route('https://fonts.gstatic.com/**', (route) => route.abort())

  await page.addInitScript(
    ([user]) => {
      localStorage.setItem('valora.token', 'e2e-token')
      localStorage.setItem('valora.user', JSON.stringify(user))
      localStorage.setItem('valora.estate', '1')
    },
    [options.user],
  )

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    calls.push({ method: request.method(), pathname: url.pathname, body: request.postData() })

    if (url.pathname === '/api/v1/auth/me') return route.fulfill({ json: options.user })
    if (url.pathname === '/api/v1/auth/estates') {
      return route.fulfill({ json: { estates: options.user.role === 'resident' ? [] : [ESTATE] } })
    }
    if (url.pathname === '/api/v1/public/estates') return route.fulfill({ json: PUBLIC_ESTATES })
    if (url.pathname === '/api/v1/residency-requests/mine') {
      return route.fulfill({ json: [] })
    }
    if (url.pathname === '/api/v1/residency-requests/pending-count') {
      return route.fulfill({ json: { pending: 1 } })
    }
    if (url.pathname === '/api/v1/residency-requests' && request.method() === 'POST') {
      return route.fulfill({ status: 201, json: PENDING_REQUEST })
    }
    if (url.pathname === '/api/v1/residency-requests') {
      return route.fulfill({
        json: { items: [PENDING_REQUEST], total: 1, page: 1, size: 20, pages: 1 },
      })
    }
    if (url.pathname.endsWith('/approve')) {
      return route.fulfill({ json: { ...PENDING_REQUEST, status: 'approved' } })
    }
    if (url.pathname.endsWith('/reject')) {
      return route.fulfill({
        json: { ...PENDING_REQUEST, status: 'rejected', decision_note: 'Not on the lease' },
      })
    }
    return route.fulfill({ json: { items: [], total: 0, page: 1, size: 20, pages: 0 } })
  })

  return calls
}

test.describe('Resident approval flow', () => {
  test('a resident picks a complex, submits for approval and is told it is pending', async ({
    page,
  }) => {
    const calls = await withMocks(page, { user: RESIDENT_USER })
    await page.setViewportSize(DESKTOP)
    await page.goto('/request-access')

    await expect(page.getByRole('heading', { name: /ask to join your estate/i })).toBeVisible()
    await expect(page.getByText(/you will not have access until they approve it/i)).toBeVisible()

    await page.getByRole('button', { name: /zambezi country estate/i }).click()
    await page.getByLabel(/unit number/i).fill('A-101')
    await page.getByLabel(/note to the estate office/i).fill('Lease starts 1 Nov')
    await page.getByRole('button', { name: /send request for approval/i }).click()

    const submit = calls.find(
      (call) => call.pathname === '/api/v1/residency-requests' && call.method === 'POST',
    )
    expect(submit, 'the request was posted').toBeTruthy()
    expect(JSON.parse(submit!.body ?? '{}')).toEqual({
      estate_id: 4,
      unit_no: 'A-101',
      note: 'Lease starts 1 Nov',
    })

    await expect(page.getByText(/request sent to zambezi country estate/i)).toBeVisible()
  })

  test('an administrator confirms, then approves, and the decision is sent', async ({ page }) => {
    const calls = await withMocks(page, { user: ADMIN_USER })
    await page.setViewportSize(DESKTOP)
    await page.goto('/admin/residency')

    await expect(page.getByText('1 awaiting review')).toBeVisible()
    await page.getByRole('row').filter({ hasText: 'Thandi Nkosi' }).click()

    const dialog = page.getByRole('dialog')
    await expect(dialog.getByText('Lease starts 1 Nov')).toBeVisible()

    // Confirmation is a distinct step: no decision is sent by the first click.
    await dialog.getByRole('button', { name: 'Approve' }).click()
    await expect(dialog.getByText(/approve thandi nkosi\?/i)).toBeVisible()
    expect(calls.some((call) => call.pathname.endsWith('/approve'))).toBe(false)

    await dialog.getByRole('button', { name: /yes, approve access/i }).click()

    await expect
      .poll(() => calls.some((call) => call.pathname === '/api/v1/residency-requests/31/approve'))
      .toBe(true)
  })

  test('an administrator rejects with a reason, and no approval is ever sent', async ({ page }) => {
    const calls = await withMocks(page, { user: ADMIN_USER })
    await page.setViewportSize(DESKTOP)
    await page.goto('/admin/residency')

    await page.getByRole('row').filter({ hasText: 'Thandi Nkosi' }).click()
    const dialog = page.getByRole('dialog')
    await dialog.getByRole('button', { name: 'Reject' }).click()
    await dialog.getByLabel(/reason/i).fill('Not on the lease')
    await dialog.getByRole('button', { name: /yes, reject the request/i }).click()

    await expect
      .poll(() => calls.find((call) => call.pathname.endsWith('/reject')))
      .toBeTruthy()
    const reject = calls.find((call) => call.pathname.endsWith('/reject'))
    expect(JSON.parse(reject!.body ?? '{}')).toEqual({ note: 'Not on the lease' })
    expect(calls.some((call) => call.pathname.endsWith('/approve'))).toBe(false)
  })
})
