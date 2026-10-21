import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import assert from 'node:assert/strict'

test('the Settings methodology describes the authoritative backend pillar weights', () => {
  const engine = readFileSync('../backend/app/analytics/engine/constants.py', 'utf8')
  const copy = readFileSync('src/lib/estateMockData.js', 'utf8')
  const labels = {
    resolution: 'Resolution', frequency: 'Frequency', security: 'Security',
    satisfaction: 'Satisfaction', infrastructure: 'Infrastructure',
  }
  const weights = engine.match(/COMPONENT_WEIGHTS:[\s\S]*?=\s*\{([\s\S]*?)\}/)?.[1]
  assert.ok(weights, 'Backend methodology must be published in constants')
  for (const [key, label] of Object.entries(labels)) {
    const value = weights.match(new RegExp(`"${key}": Decimal\\("([\\d.]+)"\\)`))?.[1]
    assert.ok(value, `Missing backend pillar: ${key}`)
    assert.ok(copy.includes(`${label} (${Number(value) * 100}%)`), `Settings must display ${label} with the backend weight`)
  }
})
