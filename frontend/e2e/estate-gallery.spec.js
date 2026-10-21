import { expect, test } from '@playwright/test';
/**
 * An estate's photograph mosaic, at desktop width.
 *
 * Vitest pins the arithmetic and the tile's behaviour. What only a browser can
 * show is that the layout survives the overflow case: that the overflow tile
 * takes the fifth slot instead of pushing the mosaic onto a sixth row, and that
 * the blur is a real filter rather than a class name that quietly does nothing.
 */
const DESKTOP = { width: 1280, height: 1000 };
// A real image, so the tile renders an <img> the browser can filter. A 404 would
// swap in the fallback box and the blur could not be measured at all.
const SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="480" height="320">
  <rect width="480" height="320" fill="#1f6f5c"/><circle cx="240" cy="160" r="90" fill="#f6f4ef"/>
</svg>`;
function photos(count) {
    return Array.from({ length: count }, (_, index) => ({
        public_id: `p${index + 1}`,
        caption: index === 0 ? 'The pool at dusk' : null,
    }));
}
async function withEstate(page, photoCount) {
    await page.route('https://fonts.googleapis.com/**', (route) => route.abort());
    await page.route('https://fonts.gstatic.com/**', (route) => route.abort());
    await page.route('**/api/v1/public/photos/**', (route) => route.fulfill({ status: 200, contentType: 'image/svg+xml', body: SVG }));
    await page.route('**/api/v1/public/estates/*', (route) => route.fulfill({
        json: {
            estate_id: 9,
            name: 'Ridge Close Estate',
            suburb: 'Centurion',
            city: 'Tshwane',
            province: 'Gauteng',
            description: 'A 24-unit complex with a single monitored gate.',
            unit_count: 24,
            photos: photos(photoCount),
            living_score: null,
        },
    }));
}
const grid = (page) => page.locator('div').filter({ has: page.getByRole('button', { name: /open photograph 1 of/i }) });
test.describe('the estate photograph mosaic', () => {
    test('counts what it cannot show, and blurs it for real', async ({ page }) => {
        await withEstate(page, 12);
        await page.setViewportSize(DESKTOP);
        await page.goto('/estates/9');
        const overflow = page.getByRole('button', {
            name: /show all 12 photographs, including 8 not shown here/i,
        });
        await expect(overflow).toBeVisible();
        await expect(overflow.getByText('+8 more')).toBeVisible();
        // Four clear tiles, then the one carrying the rest — and no fifth clear tile.
        for (let index = 1; index <= 4; index += 1) {
            await expect(page.getByRole('button', { name: new RegExp(`^open photograph ${index} of 12`, 'i') })).toBeVisible();
        }
        await expect(page.getByRole('button', { name: /^open photograph 5 of 12/i })).toHaveCount(0);
        const blur = await overflow.locator('img').evaluate((el) => getComputedStyle(el).filter);
        expect(blur).toContain('blur(3px)');
    });
    test('the overflow tile takes the fifth slot instead of growing a row', async ({ page }) => {
        await withEstate(page, 5);
        await page.setViewportSize(DESKTOP);
        await page.goto('/estates/9');
        await expect(page.getByRole('button', { name: /open photograph 5 of 5/i })).toBeVisible();
        const filled = (await grid(page).first().boundingBox());
        await withEstate(page, 20);
        await page.goto('/estates/9');
        await expect(page.getByText('+16 more')).toBeVisible();
        const overflowing = (await grid(page).first().boundingBox());
        // The same 1 + 4 arrangement either way: the mosaic ends where it ended.
        expect(Math.round(overflowing.height)).toBe(Math.round(filled.height));
    });
    test('the overflow tile opens the gallery on the first photograph it hides', async ({ page }) => {
        await withEstate(page, 12);
        await page.setViewportSize(DESKTOP);
        await page.goto('/estates/9');
        await page
            .getByRole('button', { name: /show all 12 photographs, including 8 not shown here/i })
            .click();
        const viewer = page.getByRole('dialog');
        await expect(viewer.getByText('5 of 12')).toBeVisible();
        // Every photograph is reachable from here, not only the ones that were shown.
        await page.keyboard.press('ArrowRight');
        await expect(viewer.getByText('6 of 12')).toBeVisible();
        await page.keyboard.press('Escape');
        await expect(page.getByRole('dialog')).toBeHidden();
    });
});
