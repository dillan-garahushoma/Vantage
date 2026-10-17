/**
 * Render an HTML file to a PNG with the Chromium that is already installed for
 * Playwright. No new dependency, no image API, no network.
 *
 *   node docs/design/assets/render-og.cjs <input.html> <output.png> [width] [height] [scale]
 */
const path = require('path')

const REPO = path.resolve(__dirname, '../../..')
const { chromium } = require(path.join(REPO, 'frontend/node_modules/@playwright/test'))

async function main() {
  const [input, output, w = '1200', h = '630', scale = '2'] = process.argv.slice(2)
  if (!input || !output) {
    console.error('usage: node render-og.cjs <input.html> <output.png> [w] [h] [scale]')
    process.exit(2)
  }

  const browser = await chromium.launch()
  try {
    const page = await browser.newPage({
      viewport: { width: Number(w), height: Number(h) },
      // 2× so the PNG is retina-crisp (1200×630 → 2400×1260) and crops well.
      deviceScaleFactor: Number(scale),
    })
    await page.goto('file://' + path.resolve(input))
    await page.waitForLoadState('networkidle')
    await page.evaluate(() => document.fonts.ready)

    // A fixed-size card clips silently: `overflow: hidden` on the body means an
    // over-tall layout just loses its bottom, and the PNG looks plausible. Measure
    // it instead, and refuse to write a clipped image.
    const overflow = await page.evaluate(() => {
      const limit = document.body.getBoundingClientRect().height
      const deepest = Array.from(document.querySelectorAll('body *')).reduce(
        (worst, element) => Math.max(worst, element.getBoundingClientRect().bottom),
        0,
      )
      return { limit: Math.round(limit), deepest: Math.round(deepest) }
    })
    if (overflow.deepest > overflow.limit + 0.5) {
      throw new Error(
        `content is ${overflow.deepest - overflow.limit}px taller than the ` +
          `${overflow.limit}px canvas — the bottom of the image would be clipped`,
      )
    }

    await page.screenshot({ path: path.resolve(output) })
  } finally {
    await browser.close()
  }

  console.log(`rendered ${input} → ${output}`)
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
