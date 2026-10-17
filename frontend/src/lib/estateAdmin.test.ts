/**
 * The paste-a-list parser, and the client-side upload hints.
 *
 * Neither of these is a gate — the API validates both — so the tests pin the two
 * properties that matter: a bad line is rejected *before* a batch is sent, and the
 * hints describe the same limits the server enforces (4 of them, or 5 MB, is a
 * mistake in this file, not in the contract).
 */
import { describe, expect, it } from 'vitest'

import {
  ACCEPTED_IMAGE_TYPES,
  MAX_UPLOAD_BYTES,
  UPLOAD_HINT,
  parseUnitLines,
} from './estateAdmin'

describe('parseUnitLines', () => {
  it('reads "unit_no, street address, size, bedrooms, bathrooms"', () => {
    const { lines, rejected } = parseUnitLines('A-101, 12 Ridge Close, 96, 3, 2')

    expect(rejected).toEqual([])
    expect(lines).toEqual([
      { unit_no: 'A-101', street_address: '12 Ridge Close', size_m2: 96, bedrooms: 3, bathrooms: 2 },
    ])
  })

  it('accepts a bare unit number and omits what was not given', () => {
    const { lines } = parseUnitLines('B-7')
    expect(lines).toEqual([{ unit_no: 'B-7' }])
    expect(lines[0]).not.toHaveProperty('bedrooms')
  })

  it('skips blank lines without rejecting them', () => {
    const { lines, rejected } = parseUnitLines('A-1\n\n   \nA-2')

    expect(lines.map((line) => line.unit_no)).toEqual(['A-1', 'A-2'])
    expect(rejected).toEqual([])
  })

  it('reports the line numbers it could not read, so the admin can fix the paste', () => {
    const { lines, rejected } = parseUnitLines('A-1\n, no unit\nA-3, Road, many')

    expect(rejected).toEqual([2, 3])
    expect(lines.map((line) => line.unit_no)).toEqual(['A-1'])
  })

  it('returns nothing for empty input rather than an empty unit', () => {
    expect(parseUnitLines('   \n\n')).toEqual({ lines: [], rejected: [] })
  })
})

describe('upload hints', () => {
  it('names the formats, the size ceiling and the per-estate cap in one line', () => {
    expect(ACCEPTED_IMAGE_TYPES).toEqual(['image/jpeg', 'image/png', 'image/webp'])
    expect(UPLOAD_HINT).toContain('JPEG')
    expect(UPLOAD_HINT).toContain('PNG')
    expect(UPLOAD_HINT).toContain('WebP')
    expect(UPLOAD_HINT).toContain('5 MB')
    expect(UPLOAD_HINT).toContain('12')
  })

  it('uses the same 5 MB ceiling the API documents', () => {
    expect(MAX_UPLOAD_BYTES).toBe(5 * 1024 * 1024)
  })
})
