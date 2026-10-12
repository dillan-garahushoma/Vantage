/**
 * Presentation-only guards for the two AI surfaces (BATCH AI-5).
 *
 * These are source-level assertions, deliberately blunt: the panels may show
 * what the API returns and nothing more. No score is computed here, no category
 * is inferred, and no vocabulary is retyped by hand — the allowed values come
 * from the generated contract (`src/api/generated/enums.ts`).
 *
 * The sources are read through Vite's `?raw` import, so the assertions are about
 * the text that ships, with no Node types or filesystem access needed.
 */
import { describe, expect, it } from 'vitest'

import { complaintCategories, complaintPriorities, triageTrades } from '../api/generated/enums'
import healthBriefSource from './HealthBrief.tsx?raw'
import triageSuggestionSource from './TriageSuggestion.tsx?raw'

const PANELS: Array<[string, string]> = [
  ['src/components/HealthBrief.tsx', healthBriefSource],
  ['src/components/TriageSuggestion.tsx', triageSuggestionSource],
]

function importSpecifiers(text: string): string[] {
  const found: string[] = []
  const pattern = /from\s+['"]([^'"]+)['"]/g
  let match: RegExpExecArray | null
  while ((match = pattern.exec(text)) !== null) found.push(match[1])
  return found
}

describe('AI panels — presentation only', () => {
  it.each(PANELS)('%s imports no scoring, engine or inference logic', (_name, text) => {
    const specifiers = importSpecifiers(text)

    expect(specifiers.length).toBeGreaterThan(0)
    for (const specifier of specifiers) {
      expect(specifier).not.toMatch(/(score|living|compute|calculat|engine|inference|analytics)/i)
    }
  })

  it.each(PANELS)('%s takes its vocabularies from the generated contract only', (_name, text) => {
    for (const specifier of importSpecifiers(text).filter((one) => one.includes('enum'))) {
      expect(specifier).toBe('../api/generated/enums')
    }
  })

  it('never retypes a contract vocabulary as a string literal in the panels', () => {
    const text = PANELS.map(([, source]) => source).join('\n')
    const vocabulary = new Set([...complaintCategories, ...complaintPriorities, ...triageTrades])

    for (const value of vocabulary) {
      expect(text).not.toContain(`'${value}'`)
    }
  })
})
