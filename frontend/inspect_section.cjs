const { chromium } = require('@playwright/test');

(async () => {
  const executablePath = `${process.env.LOCALAPPDATA}\\ms-playwright\\chromium-1247\\chrome-win64\\chrome.exe`;
  const browser = await chromium.launch({ executablePath, headless: true });
  const page = await browser.newPage();

  const logs = [];
  page.on('console', msg => logs.push(`[${msg.type()}] ${msg.text()}`));
  page.on('requestfailed', req => logs.push(`[FAILED] ${req.url()}: ${req.failure()?.errorText}`));
  page.on('response', res => {
    if (res.url().includes('/api/')) {
      logs.push(`[API] ${res.status()} ${res.url()}`);
    }
  });

  await page.goto('https://vantage-7k0.pages.dev/', { waitUntil: 'networkidle' });

  console.log('--- LOGS ---');
  console.log(logs.join('\n'));

  const section = await page.$('section[aria-labelledby="featured-estates"]');
  if (section) {
    console.log('--- FEATURED ESTATES HTML ---');
    console.log(await section.innerHTML());
  } else {
    console.log('section[aria-labelledby="featured-estates"] not found');
  }

  await browser.close();
})();
