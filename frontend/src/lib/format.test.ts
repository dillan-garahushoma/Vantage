/**
 * Every published vocabulary value must render as readable text, and legacy
 * free-text values (complaints filed before BE-1) must be prettified rather than
 * dropped.
 */
import { describe, expect, it } from 'vitest'

import {
  complaintCategories,
  complaintPriorities,
  triageCategories,
  triageDecisions,
  triagePriorities,
  triageTrades,
} from '../api/generated/enums'
import { displayLabel } from './format'

const publishedValues = [
  ...complaintCategories,
  ...complaintPriorities,
  ...triageCategories,
  ...triagePriorities,
  ...triageTrades,
  ...triageDecisions,
]

describe('displayLabel', () => {
  it('turns a vocabulary value into a sentence-case label', () => {
    expect(displayLabel('general_maintenance')).toBe('General maintenance')
    expect(displayLabel('pest_control')).toBe('Pest control')
    expect(displayLabel('water')).toBe('Water')
    expect(displayLabel('high')).toBe('High')
  })

  it('gives every generated value a readable label', () => {
    for (const value of publishedValues) {
      const label = displayLabel(value)
      expect(label, value).not.toBe('')
      expect(label, value).not.toContain('_')
      expect(label, value).not.toContain('-')
      expect(label[0], value).toBe(label[0].toUpperCase())
      expect(label.slice(1), value).toBe(label.slice(1).toLowerCase())
    }
  })

  it('prettifies legacy free-text categories instead of dropping them', () => {
    // Rows filed before the vocabulary existed (see seed_demo.py and older complaints).
    expect(displayLabel('plumbing')).toBe('Plumbing')
    expect(displayLabel('drainage')).toBe('Drainage')
    expect(displayLabel('roads')).toBe('Roads')
    expect(displayLabel('GENERAL')).toBe('General')
  })

  it('never returns nothing for an unknown value', () => {
    expect(displayLabel('')).toBe('—')
    expect(displayLabel('  ')).toBe('—')
  })
})
