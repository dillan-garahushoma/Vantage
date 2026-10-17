import { expect, test, type Page } from '@playwright/test'

/**
 * The estate photograph uploader, in a real browser.
 *
 * The point of this spec is the one thing jsdom cannot settle: whether a person
 * can actually choose several photographs in one trip through the file picker.
 * jsdom has no file chooser, so `multiple` and the queue behind it are only
 * genuinely proven here — by putting two files into the real control and then
 * counting the requests the app sends.
 */
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
  id: 1,
  email: 'admin@example.co.za',
  full_name: 'Nomvula Dlamini',
  role: 'hoa_admin',
  unit_no: 'A-1',
  email_verified: true,
  hoa_approved: true,
}

/**
 * Fixtures on disk, chosen through the real file picker.
 *
 * Paths rather than buffers: this project carries no Node type definitions, and
 * a file the browser genuinely reads from disk is closer to what an
 * administrator actually does. The bytes never reach a server — the upload route
 * is mocked — but the control has to hold something shaped like a photograph.
 *
 * The path is built from this module's own URL, not the working directory, so
 * the spec does not care where it was invoked from. `import.meta.url` is a web
 * standard, which is what keeps this free of Node types. On Windows a URL
 * pathname is `/C:/…`, and the file system wants `C:/…`.
 */
const fixture = (name: string) =>
  decodeURIComponent(new URL(`./fixtures/${name}`, import.meta.url).pathname).replace(
    /^\/([A-Za-z]:)/,
    '$1',
  )

interface Upload {
  filename: string
  contentType: string
}

async function withAdmin(page: Page): Promise<Upload[]> {
  const uploads: Upload[] = []

  await page.route('https://fonts.googleapis.com/**', (route) => route.abort())
  await page.route('https://fonts.gstatic.com/**', (route) => route.abort())

  await page.addInitScript(
    ([user]) => {
      localStorage.setItem('valora.token', 'e2e-token')
      localStorage.setItem('valora.user', JSON.stringify(user))
      localStorage.setItem('valora.estate', '1')
    },
    [ADMIN_USER],
  )

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())

    if (url.pathname === '/api/v1/auth/me') return route.fulfill({ json: ADMIN_USER })
    if (url.pathname === '/api/v1/auth/estates') return route.fulfill({ json: { estates: [ESTATE] } })
    if (url.pathname === '/api/v1/estates/profile') {
      return route.fulfill({
        json: {
          estate_id: 1,
          name: 'Ridge Close Estate',
          suburb: 'Centurion',
          city: 'Tshwane',
          province: 'Gauteng',
          description: null,
          is_demo: true,
          is_public: true,
          show_living_score: true,
        },
      })
    }
    if (url.pathname === '/api/v1/estates/photos' && request.method() === 'POST') {
      // The body is multipart; the filename is enough to prove which file this
      // request carried, and that there was one request per file.
      uploads.push({
        filename: /filename="([^"]+)"/.exec(request.postData() ?? '')?.[1] ?? 'unknown',
        contentType: request.headers()['content-type'] ?? '',
      })
      return route.fulfill({
        status: 201,
        json: {
          photo_id: uploads.length,
          public_id: `pub${uploads.length}`,
          caption: null,
          position: 0,
          width: 1920,
          height: 1280,
          bytes: 1024,
          created_at: '2026-10-13T09:00:00Z',
        },
      })
    }
    if (url.pathname === '/api/v1/estates/photos') return route.fulfill({ json: [] })
    if (url.pathname === '/api/v1/join-codes/current') {
      return route.fulfill({ status: 404, json: { detail: 'No join code' } })
    }
    if (url.pathname === '/api/v1/properties') {
      return route.fulfill({ json: { items: [], total: 0, page: 1, size: 100, pages: 0 } })
    }
    if (request.method() === 'GET') {
      return route.fulfill({ json: { items: [], total: 0, page: 1, size: 20, pages: 0 } })
    }
    return route.fulfill({ json: {} })
  })

  return uploads
}

test.describe('the estate photograph uploader', () => {
  test('takes several photographs from one trip through the picker', async ({ page }) => {
    const uploads = await withAdmin(page)
    await page.goto('/admin/setup')

    const picker = page.getByLabel(/choose photographs to upload/i)
    // The setup screen loads its estate, its units, its photographs and its join
    // code before it paints; on a cold dev server that is not a 5s wait.
    await expect(picker).toBeAttached({ timeout: 30_000 })
    await expect(picker).toHaveAttribute('multiple', '')

    // One interaction, two files — the complaint this spec exists to settle.
    await picker.setInputFiles([fixture('pool.png'), fixture('gate.png')])

    await expect(page.getByText(/2 photographs queued/)).toBeVisible()
    // Exact: each row also carries a visually hidden "Caption for <name>" label.
    await expect(page.getByText('pool.png', { exact: true })).toBeVisible()
    await expect(page.getByText('gate.png', { exact: true })).toBeVisible()

    // Each row has a live preview, not a placeholder.
    const previews = page.locator('li img')
    await expect(previews).toHaveCount(2)
    for (const src of await previews.evaluateAll((imgs) => imgs.map((img) => img.getAttribute('src')))) {
      expect(src).toMatch(/^blob:/)
    }

    // A second selection adds to the queue rather than replacing it.
    await picker.setInputFiles([fixture('court.png')])
    await expect(page.getByText(/3 photographs queued/)).toBeVisible()

    await page.getByRole('button', { name: 'Upload 3 photographs' }).click()

    // One request per photograph, each carrying its own file.
    await expect.poll(() => uploads.length).toBe(3)
    expect(uploads.map((upload) => upload.filename).sort()).toEqual([
      'court.png',
      'gate.png',
      'pool.png',
    ])
    for (const upload of uploads) expect(upload.contentType).toContain('multipart/form-data')

    // And the queue is empty afterwards, because the estate's own list shows them.
    await expect(page.getByText('3 photographs uploaded.')).toBeVisible()
    await expect(page.locator('li img')).toHaveCount(0)
  })

  test('says which file it will not send, and sends the rest', async ({ page }) => {
    const uploads = await withAdmin(page)
    await page.goto('/admin/setup')

    const picker = page.getByLabel(/choose photographs to upload/i)
    await expect(picker).toBeAttached({ timeout: 30_000 })
    // A text file cannot match the control's `accept`, but the picker is not the
    // only way in — a drop or a renamed extension reaches the component too, and
    // it has to decide then.
    await picker.setInputFiles([fixture('pool.png'), fixture('notes.txt')])

    await expect(page.getByText(/cannot be sent: not jpeg, png, webp/i)).toBeVisible()
    await expect(page.getByText('pool.png', { exact: true })).toBeVisible()

    await page.getByRole('button', { name: 'Upload 1 photograph' }).click()

    await expect.poll(() => uploads.map((upload) => upload.filename)).toEqual(['pool.png'])
  })
})
