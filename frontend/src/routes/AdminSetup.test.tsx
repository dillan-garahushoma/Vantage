/**
 * The setup checklist.
 *
 * Every tick is derived from what the API returned, so the screen cannot claim an
 * estate is ready when it is not — and it cannot nag about work that is already
 * done. A missing count (`null`, because the request failed) is deliberately *not*
 * treated as zero.
 */
import { describe, expect, it } from 'vitest'

import { setupChecklist } from './AdminSetup'
import type { EstateProfile } from '../lib/contract'

function profile(overrides: Partial<EstateProfile> = {}): EstateProfile {
  return {
    estate_id: 1,
    name: 'Ridge Close',
    suburb: 'Centurion',
    city: 'Tshwane',
    province: 'Gauteng',
    description: null,
    is_demo: false,
    is_public: false,
    show_living_score: false,
    ...overrides,
  }
}

function byKey(input: Parameters<typeof setupChecklist>[0]) {
  return Object.fromEntries(setupChecklist(input).map((item) => [item.key, item.done]))
}

describe('setupChecklist', () => {
  it('reports every step outstanding for a brand-new estate', () => {
    const state = byKey({ profile: profile(), unitCount: 0, photoCount: 0, hasJoinCode: false })

    expect(state).toEqual({
      description: false,
      units: false,
      'join-code': false,
      photos: false,
      publish: false,
    })
  })

  it('ticks each step from the API’s own values', () => {
    const state = byKey({
      profile: profile({ description: 'A 24-unit complex.', is_public: true }),
      unitCount: 24,
      photoCount: 3,
      hasJoinCode: true,
    })

    expect(Object.values(state)).toEqual([true, true, true, true, true])
  })

  it('does not count a whitespace-only description as done', () => {
    const state = byKey({
      profile: profile({ description: '   ' }),
      unitCount: 0,
      photoCount: 0,
      hasJoinCode: null,
    })
    expect(state.description).toBe(false)
  })

  it('treats an unanswered request as unknown, not as zero', () => {
    const state = byKey({ profile: profile(), unitCount: null, photoCount: null, hasJoinCode: null })

    expect(state.units).toBe(false)
    expect(state.photos).toBe(false)
    expect(state['join-code']).toBe(false)
  })

  it('requires publishing separately from a description', () => {
    const state = byKey({
      profile: profile({ description: 'Done.', is_public: false }),
      unitCount: 10,
      photoCount: 1,
      hasJoinCode: true,
    })
    expect(state.publish).toBe(false)
    expect(state.description).toBe(true)
  })

  it('names five steps', () => {
    expect(setupChecklist({ profile: null, unitCount: null, photoCount: null, hasJoinCode: null })).toHaveLength(5)
  })
})
