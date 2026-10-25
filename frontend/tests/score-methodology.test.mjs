import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import assert from 'node:assert/strict'

test('the methodology explains the backend coverage floor without requiring all five pillars', () => {
  const engine = readFileSync('../backend/app/analytics/engine/constants.py', 'utf8')
  const copy = readFileSync('src/routes/Methodology.jsx', 'utf8')
  const floor = engine.match(/MEASURED_WEIGHT_FLOOR:[^\n]+Decimal\("([\d.]+)"\)/)?.[1]
  assert.ok(floor)
  assert.ok(copy.includes(`at least ${Number(floor) * 100}% of the total weight`))
  assert.doesNotMatch(copy, /All five pillars must have at least one data point/)
})

test('the public methodology displays the authoritative backend pillar weights', () => {
  const engine = readFileSync('../backend/app/analytics/engine/constants.py', 'utf8')
  const copy = readFileSync('src/components/LivingScore.jsx', 'utf8')
  const weights = engine.match(/COMPONENT_WEIGHTS:[\s\S]*?=\s*\{([\s\S]*?)\}/)?.[1]
  assert.ok(weights, 'Backend methodology must be published in constants')
  for (const key of ['resolution', 'frequency', 'security', 'satisfaction', 'infrastructure']) {
    const value = weights.match(new RegExp(`"${key}": Decimal\\("([\\d.]+)"\\)`))?.[1]
    assert.ok(value, `Missing backend pillar: ${key}`)
    const displayed = copy.match(new RegExp(`key: '${key}'[^\\n]+weight: ([\\d.]+)`))?.[1]
    assert.equal(Number(displayed), Number(value), `${key} must display the backend weight`)
  }
})
