const { chromium } = require('@playwright/test');

(async () => {
  const executablePath = `${process.env.LOCALAPPDATA}\\ms-playwright\\chromium-1247\\chrome-win64\\chrome.exe`;
  const browser = await chromium.launch({
    executablePath,
    headless: true,
  });
  const context = await browser.newContext();
  const page = await context.newPage();

  const logs = [];
  page.on('console', msg => logs.push(`[${msg.type()}] ${msg.text()}`));
  page.on('requestfailed', req => logs.push(`[FAILED] ${req.url()}: ${req.failure()?.errorText}`));
  page.on('response', res => {
    if (res.url().includes('/api/')) {
      logs.push(`[API] ${res.status()} ${res.url()}`);
    }
  });

  await page.goto('https://vantage-7k0.pages.dev/', { waitUntil: 'networkidle' });

  const bodyText = await page.innerText('body');
  console.log('--- LOGS ---');
  console.log(logs.join('\n'));
  console.log('--- BODY TEXT (first 1000 chars) ---');
  console.log(bodyText.slice(0, 1000));

  await browser.close();
})().catch(err => {
  console.error(err);
  process.exit(1);
});
