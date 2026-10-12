/**
 * The complaint form must offer exactly the values the API accepts.
 *
 * The old hand-copied list offered `plumbing`, `drainage`, `roads`, `garden` and
 * `general` — none of them in the vocabulary — and hid `water`, `infrastructure`,
 * `waste`, `parking` and `administrative`. These tests fail if a hand-written list
 * ever creeps back in.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { complaintCategories, complaintPriorities } from '../api/generated/enums'
import { displayLabel } from '../lib/format'

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, role: 'resident' }, checking: false }),
}))

vi.mock('../context/EstateContext', () => ({
  useEstateScope: () => ({
    estateId: 1,
    estate: { estate_id: 1, estate_name: 'Test Estate', property_ids: [7] },
  }),
}))

vi.mock('../lib/api', () => ({
  ApiError: class ApiError extends Error {},
  api: {
    get: vi.fn(async () => ({
      items: [{ id: 7, unit_no: 'A-101', street_address: '1 Test Road' }],
      total: 1,
      page: 1,
      size: 20,
      pages: 1,
    })),
  },
}))

import { LogComplaintDrawer } from './Complaints'

function optionValues(select: HTMLElement): string[] {
  return Array.from(select.querySelectorAll('option')).map((option) => option.value)
}

function optionLabels(select: HTMLElement): string[] {
  return Array.from(select.querySelectorAll('option')).map((option) => option.textContent ?? '')
}

describe('LogComplaintDrawer options', () => {
  it('renders exactly the published categories, in contract order', async () => {
    render(<LogComplaintDrawer onClose={() => {}} onDone={() => {}} />)

    const category = await screen.findByLabelText('Category')

    expect(optionValues(category)).toEqual([...complaintCategories])
    expect(optionLabels(category)).toEqual(complaintCategories.map(displayLabel))
  })

  it('renders exactly the published priorities', async () => {
    render(<LogComplaintDrawer onClose={() => {}} onDone={() => {}} />)

    const priority = await screen.findByLabelText('Priority')

    expect(optionValues(priority)).toEqual([...complaintPriorities])
    expect(optionLabels(priority)).toEqual(complaintPriorities.map(displayLabel))
  })

  it('offers no value the API would reject', async () => {
    render(<LogComplaintDrawer onClose={() => {}} onDone={() => {}} />)

    const offered = [
      ...optionValues(await screen.findByLabelText('Category')),
      ...optionValues(await screen.findByLabelText('Priority')),
    ]

    for (const stale of ['plumbing', 'drainage', 'roads', 'garden', 'general']) {
      expect(offered, stale).not.toContain(stale)
    }
  })
})
