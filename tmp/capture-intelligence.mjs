import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'

const OUT = new URL('./screenshots/', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')
mkdirSync(OUT, { recursive: true })

const BASE = 'http://127.0.0.1:5173'
const shots = []
const consoleErrors = []

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 })
page.on('console', (msg) => {
  if (msg.type() === 'error') consoleErrors.push(msg.text())
})
page.on('pageerror', (err) => consoleErrors.push(`pageerror: ${err.message}`))

await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' })
await page.fill('input[type="email"], input[name="email"]', 'hoa.silverleaf@example.com')
await page.fill('input[type="password"]', 'ValoraDemo!2026')
await page.click('button[type="submit"]')
await page.waitForURL(/\/(app|admin)/, { timeout: 20000 })

const routes = [
  ['intelligence', '/intelligence'],
  ['dashboard', '/app'],
  ['complaints', '/app/complaints'],
  ['work-orders', '/app/work-orders'],
  ['members', '/admin/members'],
]

for (const [name, path] of routes) {
  await page.goto(`${BASE}${path}`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1200)
  await page.screenshot({ path: `${OUT}/${name}-viewport.png` })
  await page.screenshot({ path: `${OUT}/${name}-full.png`, fullPage: true })
  const heading = await page.locator('h1').first().textContent().catch(() => null)
  shots.push({ name, path, url: page.url(), heading: heading?.trim() ?? null })
}

await page.goto(`${BASE}/intelligence`, { waitUntil: 'networkidle' })
await page.waitForTimeout(1200)

const evidence = await page.evaluate(() => {
  const text = (sel) => document.querySelector(sel)?.textContent?.replace(/\s+/g, ' ').trim() ?? null
  const cs = (sel, prop) => {
    const el = document.querySelector(sel)
    return el ? getComputedStyle(el).getPropertyValue(prop) : null
  }
  const body = getComputedStyle(document.body)
  return {
    title: document.title,
    h1: text('h1'),
    h2s: [...document.querySelectorAll('h2')].map((n) => n.textContent.replace(/\s+/g, ' ').trim()),
    bodyFont: body.fontFamily,
    bodyBg: body.backgroundColor,
    primaryButton: {
      bg: cs('button[data-variant="primary"], .bg-accent, button', 'background-color'),
      radius: cs('button', 'border-radius'),
    },
    canvases: [...document.querySelectorAll('section, article')].length,
    cardRadii: [...document.querySelectorAll('[class*="rounded"]')]
      .slice(0, 6)
      .map((n) => getComputedStyle(n).borderRadius),
    askValora: text('[data-testid="ask-valora"], aside'),
    hasSignalField: Boolean(document.querySelector('[data-testid="signal-field"], .signal-field')),
    navLabels: [...document.querySelectorAll('nav a')].map((a) => a.textContent.replace(/\s+/g, ' ').trim()),
  }
})

console.log(JSON.stringify({ shots, evidence, consoleErrors }, null, 2))
await browser.close()
