import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const OUT = 'tmp/ux-review';
mkdirSync(OUT, { recursive: true });

const BASE = 'http://localhost:5173';

const mockEstates = [
  {
    estate_id: 1,
    name: 'Silverleaf Reserve',
    suburb: 'Ballito',
    city: 'KwaDukuza',
    province: 'KwaZulu-Natal',
    unit_count: 120,
    cover_photo_public_id: 'sample-ballito-pool',
    description: 'Premier private coastal residential complex with 24/7 access control, clubhouse, communal pool, and active HOA management.',
    living_score: {
      overall_score: 84.2,
      status: 'scored',
      as_of: '2026-10-23T12:00:00Z',
      engine_version: 'v2.1',
    },
  },
  {
    estate_id: 2,
    name: 'Hout Bay Heights',
    suburb: 'Hout Bay',
    city: 'Cape Town',
    province: 'Western Cape',
    unit_count: 85,
    cover_photo_public_id: 'sample-cape-town',
    description: 'Mountain-facing estate in the Atlantic seaboard with landscaped gardens, solar-backed gatehouse and borehole infrastructure.',
    living_score: {
      overall_score: 91.0,
      status: 'scored',
      as_of: '2026-10-23T12:00:00Z',
      engine_version: 'v2.1',
    },
  },
  {
    estate_id: 3,
    name: 'Sandton Ridge Estate',
    suburb: 'Morningside',
    city: 'Sandton',
    province: 'Gauteng',
    unit_count: 140,
    cover_photo_public_id: 'sample-sandton',
    description: 'Secure urban complex featuring biometric perimeter security, high-speed fiber backbone, and prompt maintenance response SLA.',
    living_score: {
      overall_score: 78.5,
      status: 'scored',
      as_of: '2026-10-23T12:00:00Z',
      engine_version: 'v2.1',
    },
  },
];

const mockDetail = {
  ...mockEstates[0],
  photos: [
    { public_id: 'photo-pool', caption: 'Communal swimming pool and sundeck' },
    { public_id: 'photo-patio', caption: 'Private covered patio and outdoor entertainment area' },
    { public_id: 'photo-lounge', caption: 'Spacious open-plan living and dining area' },
    { public_id: 'photo-aerial', caption: 'Aerial view of coastal greenbelt' },
    { public_id: 'photo-gatehouse', caption: 'Secure monitored estate gatehouse' },
  ],
};

async function run() {
  const browser = await chromium.launch({ headless: true });

  const setupInterceptions = async (page) => {
    await page.route('**/api/v1/public/estates?**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: mockEstates,
          total: mockEstates.length,
          page: 1,
          pages: 1,
          page_size: 12,
        }),
      });
    });

    await page.route('**/api/v1/public/estates/1', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDetail),
      });
    });

    await page.route('**/api/v1/public/photos/**', async (route) => {
      // 1x1 transparent png pixel or svg
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">
        <rect width="800" height="600" fill="#2d283e"/>
        <text x="50%" y="50%" fill="#ffffff" font-family="sans-serif" font-size="28" text-anchor="middle" dy=".3em">VALORA Estate Visual</text>
      </svg>`;
      await route.fulfill({
        status: 200,
        contentType: 'image/svg+xml',
        body: svg,
      });
    });
  };

  // 1. Desktop Landing
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
    await setupInterceptions(page);
    await page.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${OUT}/landing-desktop-v2.png`, fullPage: false });
    console.log('Saved landing-desktop-v2.png');
    await page.close();
  }

  // 2. Mobile Landing
  {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    await setupInterceptions(page);
    await page.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${OUT}/landing-mobile-v2.png`, fullPage: false });
    console.log('Saved landing-mobile-v2.png');
    await page.close();
  }

  // 3. Desktop Directory
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
    await setupInterceptions(page);
    await page.goto(`${BASE}/estates`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${OUT}/directory-desktop-v2.png`, fullPage: false });
    console.log('Saved directory-desktop-v2.png');
    await page.close();
  }

  // 4. Desktop Detail (Airbnb style photo grid + sticky card)
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
    await setupInterceptions(page);
    await page.goto(`${BASE}/estates/1`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${OUT}/detail-desktop-v2.png`, fullPage: false });
    console.log('Saved detail-desktop-v2.png');
    await page.close();
  }

  // 5. Mobile Detail
  {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    await setupInterceptions(page);
    await page.goto(`${BASE}/estates/1`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${OUT}/detail-mobile-v2.png`, fullPage: false });
    console.log('Saved detail-mobile-v2.png');
    await page.close();
  }

  await browser.close();
  console.log('All visual verification captures complete!');
}

run().catch((err) => {
  console.error('Capture error:', err);
  process.exit(1);
});
