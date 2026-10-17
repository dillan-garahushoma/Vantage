/**
 * The provider's own work list.
 *
 * The buttons offered must match the server's state machine exactly —
 * `assigned → in_progress → completed`, with completion final — so the screen
 * never invites a transition the API will refuse, and a refusal that does come
 * back is shown verbatim rather than hidden.
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../lib/api'
import type { WorkOrder } from '../lib/contract'
import { ProviderWork } from './ProviderWork'

const mocks = vi.hoisted(() => ({ mine: vi.fn(), update: vi.fn() }))

vi.mock('../lib/estateAdmin', () => ({
  listMyWorkOrders: mocks.mine,
  updateWorkOrder: mocks.update,
}))

let role: string | null = 'service_provider'

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, full_name: 'Sipho Mokoena', role } }),
}))

vi.mock('../context/EstateContext', () => ({
  useEstateScope: () => ({
    estateId: 1,
    estate: { estate_id: 1, estate_name: 'Ridge Close' },
    loading: false,
    error: null,
    reload: vi.fn(),
  }),
  useEstate: () => ({
    estates: [],
    active: { estate_id: 1, estate_name: 'Ridge Close' },
    loading: false,
    error: null,
    awaitingProvisioning: false,
    selectEstate: vi.fn(),
    reload: vi.fn(),
  }),
}))

function order(overrides: Partial<WorkOrder> = {}): WorkOrder {
  return {
    id: 42,
    complaint_id: 7,
    provider_id: 3,
    assigned_at: '2026-10-01T08:00:00Z',
    resolved_at: null,
    job_cost: '1250.00',
    resident_rating: null,
    completion_notes: null,
    status: 'assigned',
    estimated_completion_date: '2026-10-08T08:00:00Z',
    actual_completion_date: null,
    created_at: '2026-10-01T08:00:00Z',
    updated_at: null,
    ...overrides,
  }
}

function pageOf(items: WorkOrder[]) {
  return { items, total: items.length, page: 1, size: 20, pages: 1 }
}

function renderWork() {
  return render(
    <MemoryRouter>
      <ProviderWork />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  role = 'service_provider'
  mocks.mine.mockReset()
  mocks.update.mockReset()
})

describe('ProviderWork — states', () => {
  it('sends a provider with nothing assigned to wait for the estate, not to look for work', async () => {
    mocks.mine.mockResolvedValue(pageOf([]))
    renderWork()

    expect(await screen.findByText('Nothing assigned to you yet')).toBeVisible()
    expect(screen.getByText(/has to add your email to their estate/i)).toBeVisible()
    expect(screen.getByRole('button', { name: /check again/i })).toBeVisible()
  })

  it('keeps the list for someone who is not a provider', async () => {
    role = 'hoa_admin'
    renderWork()

    expect(await screen.findByText(/service provider’s own work list/i)).toBeVisible()
    expect(mocks.mine).not.toHaveBeenCalled()
  })

  it('shows a rejected load with the server’s message and a retry', async () => {
    mocks.mine.mockRejectedValue(
      new ApiError(403, 'You are not a member of this estate.', 'FORBIDDEN', 'req-403'),
    )
    renderWork()

    expect(await screen.findByText(/could not load your work/i)).toBeVisible()
    expect(screen.getByText(/req-403/)).toBeVisible()
  })

  it('renders the figures the API returned, without recomputing any of them', async () => {
    mocks.mine.mockResolvedValue(pageOf([order()]))
    renderWork()

    expect(await screen.findByText('WO-0042')).toBeVisible()
    expect(screen.getByText('complaint #7')).toBeVisible()
    expect(screen.getByText('R 1 250')).toBeVisible()
    expect(screen.getByText('Not rated yet')).toBeVisible()
  })
})

describe('ProviderWork — transitions', () => {
  it('offers exactly one action on a newly assigned job: start the work', async () => {
    mocks.mine.mockResolvedValue(pageOf([order()]))
    renderWork()

    expect(await screen.findByRole('button', { name: /start this work/i })).toBeVisible()
    expect(screen.queryByRole('button', { name: /mark as completed/i })).toBeNull()
  })

  it('starts the work with the one status the API accepts', async () => {
    mocks.mine.mockResolvedValue(pageOf([order()]))
    mocks.update.mockResolvedValue(order({ status: 'in_progress' }))
    const user = userEvent.setup()
    renderWork()

    await user.click(await screen.findByRole('button', { name: /start this work/i }))

    expect(mocks.update).toHaveBeenCalledWith(1, 42, { status: 'in_progress' })
    expect(mocks.mine).toHaveBeenCalledTimes(2)
  })

  it('asks for the evidence note before completing, and records it as the resolution', async () => {
    mocks.mine.mockResolvedValue(pageOf([order({ status: 'in_progress' })]))
    mocks.update.mockResolvedValue(order({ status: 'completed' }))
    const user = userEvent.setup()
    renderWork()

    await user.click(await screen.findByRole('button', { name: /mark as completed/i }))
    expect(mocks.update).not.toHaveBeenCalled()
    expect(screen.getByText(/recorded against the complaint as the resolution/i)).toBeVisible()

    await user.type(screen.getByLabelText(/what was done/i), 'Replaced the seized valve.')
    await user.click(screen.getByRole('button', { name: /complete this job/i }))

    expect(mocks.update).toHaveBeenCalledWith(1, 42, {
      status: 'completed',
      completion_notes: 'Replaced the seized valve.',
    })
  })

  it('says completing is final before it is done', async () => {
    mocks.mine.mockResolvedValue(pageOf([order({ status: 'in_progress' })]))
    const user = userEvent.setup()
    renderWork()

    await user.click(await screen.findByRole('button', { name: /mark as completed/i }))

    expect(screen.getByText(/does not allow a completed job to be re-opened/i)).toBeVisible()
  })

  it('shows a refused transition as the server described it', async () => {
    mocks.mine.mockResolvedValue(pageOf([order({ status: 'in_progress' })]))
    mocks.update.mockRejectedValue(
      new ApiError(409, 'A completed work order cannot be re-opened or modified.', 'CONFLICT', 'req-409'),
    )
    const user = userEvent.setup()
    renderWork()

    await user.click(await screen.findByRole('button', { name: /mark as completed/i }))
    await user.click(screen.getByRole('button', { name: /complete this job/i }))

    expect(await screen.findByText(/not allowed from where this job is/i)).toBeVisible()
    expect(screen.getByText(/cannot be re-opened or modified/i)).toBeVisible()
    expect(screen.getByText(/req-409/)).toBeVisible()
  })

  it('offers no action on a finished job, and says what it means', async () => {
    mocks.mine.mockResolvedValue(
      pageOf([order({ status: 'completed', completion_notes: 'New gate motor fitted.' })]),
    )
    renderWork()

    expect(await screen.findByText('New gate motor fitted.')).toBeVisible()
    expect(screen.getByText(/closed on the estate’s record/i)).toBeVisible()
    expect(screen.queryByRole('button', { name: /start this work|mark as completed/i })).toBeNull()
  })

  it('filters by status in the browser and can clear the filter', async () => {
    mocks.mine.mockResolvedValue(pageOf([order()]))
    const user = userEvent.setup()
    renderWork()
    await screen.findByText('WO-0042')

    await user.selectOptions(screen.getByLabelText('Status'), 'completed')

    expect(await screen.findByText('No job with that status')).toBeVisible()
    await user.click(screen.getByRole('button', { name: /clear the filter/i }))
    await waitFor(() => expect(screen.getByText('WO-0042')).toBeVisible())
  })
})
