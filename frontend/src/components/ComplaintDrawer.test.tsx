/**
 * The complaint drawer: assigning a provider, and a resident rating the repair.
 *
 * Three things this file holds down, all of them regressions that would look fine
 * in a unit test and break in the product:
 *
 * 1. The provider picker asks the **estate-scoped** directory. The endpoint now
 *    requires `estate_id`; a request without it is a 422 and the administrator
 *    simply cannot assign anybody.
 * 2. The resident sees the work order raised for their complaint through the
 *    per-complaint endpoint, and a complaint with none is a state, not an error.
 * 3. The rating control appears only once the work is completed, and it posts the
 *    number the resident chose — credited to them, never inferred.
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../lib/api'
import type { Complaint, WorkOrder } from '../lib/types'
import { ComplaintDrawer } from './ComplaintDrawer'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  providers: vi.fn(),
  workOrder: vi.fn(),
  rate: vi.fn(),
  role: 'hoa_admin',
}))

vi.mock('../lib/api', () => ({
  ApiError: class ApiError extends Error {
    readonly status: number
    readonly code?: string
    readonly requestId?: string
    constructor(status: number, message: string, code?: string, requestId?: string) {
      super(message)
      this.status = status
      this.code = code
      this.requestId = requestId
    }
  },
  api: { get: mocks.get, post: mocks.post, patch: mocks.patch, remove: vi.fn() },
}))

vi.mock('../lib/estateAdmin', () => ({
  listEstateProviders: mocks.providers,
  getComplaintWorkOrder: mocks.workOrder,
  rateWorkOrder: mocks.rate,
}))

vi.mock('../lib/ai', () => ({
  readTriageSuggestion: vi.fn(async () => {
    throw new ApiError(404, 'No suggestion stored.')
  }),
  requestTriageSuggestion: vi.fn(),
  decideTriageSuggestion: vi.fn(),
  isAiUnavailable: () => false,
}))

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, role: mocks.role }, checking: false }),
}))

vi.mock('../context/EstateContext', () => ({
  useEstateScope: () => ({
    estateId: 4,
    estate: { estate_id: 4, estate_name: 'Ridge Close' },
    loading: false,
    error: null,
    reload: vi.fn(),
  }),
}))

function complaint(overrides: Partial<Complaint> = {}): Complaint {
  return {
    id: 11,
    user_id: 7,
    estate_id: 4,
    unit_id: 3,
    category: 'water',
    description: 'Burst pipe under the kitchen sink.',
    priority: 'high',
    is_anonymous: false,
    status: 'reviewed',
    assigned_to: null,
    reviewed_at: '2026-10-01T06:00:00Z',
    assigned_at: null,
    started_at: null,
    resolved_at: null,
    created_at: '2026-09-30T06:00:00Z',
    updated_at: null,
    ...overrides,
  }
}

function workOrder(overrides: Partial<WorkOrder> = {}): WorkOrder {
  return {
    id: 42,
    complaint_id: 11,
    provider_id: 2,
    assigned_at: '2026-10-02T06:00:00Z',
    resolved_at: null,
    job_cost: '1850.00',
    resident_rating: null,
    completion_notes: null,
    status: 'assigned',
    estimated_completion_date: null,
    actual_completion_date: null,
    created_at: '2026-10-02T06:00:00Z',
    updated_at: null,
    ...overrides,
  }
}

function renderDrawer() {
  return render(<ComplaintDrawer complaintId={11} onClose={() => {}} onChanged={() => {}} />)
}

beforeEach(() => {
  mocks.role = 'hoa_admin'
  mocks.get.mockReset()
  mocks.post.mockReset()
  mocks.patch.mockReset()
  mocks.providers.mockReset()
  mocks.workOrder.mockReset()
  mocks.rate.mockReset()

  mocks.get.mockImplementation(async (path: string) => {
    if (path === '/api/v1/complaints/11') return complaint()
    if (path === '/api/v1/complaints/11/events') return []
    return { items: [], total: 0, page: 1, size: 10, pages: 0 }
  })
})

describe('ComplaintDrawer — assigning a provider', () => {
  it('asks the estate-scoped provider directory for this estate', async () => {
    mocks.providers.mockResolvedValue({
      items: [
        { id: 2, full_name: 'Sipho Dlamini', trade: 'plumbing', verified: true },
      ],
      total: 1,
      page: 1,
      size: 100,
      pages: 1,
    })

    renderDrawer()

    await screen.findByText('No active work order. Assign a verified provider to start the resolution clock.')
    await waitFor(() => expect(mocks.providers).toHaveBeenCalledWith(4, { size: 100 }))
    expect(await screen.findByRole('option', { name: /Sipho Dlamini/ })).toBeVisible()
  })

  it('creates the work order with the complaint, the provider and the estate', async () => {
    mocks.providers.mockResolvedValue({
      items: [{ id: 2, full_name: 'Sipho Dlamini', trade: 'plumbing', verified: true }],
      total: 1,
      page: 1,
      size: 100,
      pages: 1,
    })
    mocks.post.mockResolvedValue(workOrder())
    const user = userEvent.setup()

    renderDrawer()

    await user.selectOptions(await screen.findByLabelText(/Verified provider/), '2')
    await user.click(screen.getByRole('button', { name: /assign provider/i }))

    expect(mocks.post).toHaveBeenCalledWith(
      '/api/v1/work-orders',
      { complaint_id: 11, provider_id: 2, job_cost: null },
      { estate_id: 4 },
    )
  })
})

describe('ComplaintDrawer — the resident’s repair', () => {
  it('shows the work order raised for the complaint', async () => {
    mocks.role = 'resident'
    mocks.workOrder.mockResolvedValue(workOrder({ status: 'in_progress' }))

    renderDrawer()

    expect(await screen.findByText('WO-0042')).toBeVisible()
    expect(screen.getByText('In progress')).toBeVisible()
    expect(screen.queryByText(/No work order has been raised/)).toBeNull()
  })

  it('treats a complaint with no work order as a state, not an error', async () => {
    mocks.role = 'resident'
    mocks.workOrder.mockRejectedValue(new ApiError(404, 'No work order exists for this complaint.'))

    renderDrawer()

    expect(await screen.findByText(/No work order has been raised for this complaint yet/)).toBeVisible()
  })

  it('offers no rating until the work is completed', async () => {
    mocks.role = 'resident'
    mocks.workOrder.mockResolvedValue(workOrder({ status: 'in_progress' }))

    renderDrawer()

    await screen.findByText('WO-0042')
    expect(screen.queryByRole('button', { name: /rate the repair/i })).toBeNull()
  })

  it('posts the resident’s own rating once the work is completed', async () => {
    mocks.role = 'resident'
    mocks.workOrder
      .mockResolvedValueOnce(
        workOrder({ status: 'completed', completion_notes: 'Replaced the valve.' }),
      )
      .mockResolvedValue(
        workOrder({
          status: 'completed',
          completion_notes: 'Replaced the valve.',
          resident_rating: 4,
        }),
      )
    mocks.rate.mockResolvedValue(workOrder({ status: 'completed', resident_rating: 4 }))
    const user = userEvent.setup()

    renderDrawer()

    await screen.findByText('Replaced the valve.')
    await user.click(screen.getByRole('button', { name: /rate the repair 4 out of 5/i }))

    expect(mocks.rate).toHaveBeenCalledWith(4, 42, 4)
    expect(await screen.findByText(/You rated this repair 4 out of 5/)).toBeVisible()
  })

  it('shows the refusal verbatim when the rating is rejected', async () => {
    mocks.role = 'resident'
    mocks.workOrder.mockResolvedValue(workOrder({ status: 'completed' }))
    mocks.rate.mockRejectedValue(
      new ApiError(409, 'This work order has already been rated.', 'CONFLICT', 'req-409'),
    )
    const user = userEvent.setup()

    renderDrawer()

    await user.click(await screen.findByRole('button', { name: /rate the repair 5 out of 5/i }))

    expect(await screen.findByText('This work order has already been rated.')).toBeVisible()
    expect(screen.getByText(/req-409/)).toBeVisible()
  })
})
