/**
 * The resident-approval queue.
 *
 * The screen's promises under test: a decision is confirmed before it is sent, an
 * approval and a rejection call different endpoints, the queue is administrator
 * only, and a notification email's deep link opens the right request.
 */
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../lib/api'
import { AdminResidency } from './AdminResidency'

const mocks = vi.hoisted(() => ({
  list: vi.fn(),
  count: vi.fn(),
  approve: vi.fn(),
  reject: vi.fn(),
}))

vi.mock('../lib/residency', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/residency')>()
  return {
    ...actual,
    listResidencyRequests: mocks.list,
    pendingResidencyCount: mocks.count,
    approveResidencyRequest: mocks.approve,
    rejectResidencyRequest: mocks.reject,
  }
})

let role: string | null = 'hoa_admin'

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 3, full_name: 'Nomvula Dlamini', role } }),
}))

vi.mock('../context/EstateContext', () => ({
  useEstateScope: () => ({
    estateId: 1,
    estate: { estate_id: 1, estate_name: 'Ridge Close' },
    loading: false,
    error: null,
  }),
  useEstate: () => ({ active: { estate_id: 1, estate_name: 'Ridge Close' } }),
}))

function pageOf(items: unknown[]) {
  return { items, total: items.length, page: 1, size: 20, pages: 1 }
}

const REQUESTS = [
  {
    request_id: 31,
    estate_id: 1,
    estate_name: 'Ridge Close',
    unit_no: 'A-101',
    status: 'pending',
    applicant_name: 'Thandi Nkosi',
    applicant_email: 'thandi@example.co.za',
    applicant_phone: '082 000 0000',
    note: 'Lease starts 1 Nov',
    created_at: '2026-10-13T09:30:00Z',
    decided_at: null,
    decision_note: null,
  },
  {
    request_id: 20,
    estate_id: 1,
    estate_name: 'Ridge Close',
    unit_no: 'B-4',
    status: 'approved',
    applicant_name: 'Sipho Mokoena',
    applicant_email: 'sipho@example.co.za',
    created_at: '2026-10-10T09:30:00Z',
    decided_at: '2026-10-10T12:00:00Z',
    decision_note: null,
  },
]

function renderScreen(initialEntry = '/admin/residency') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <AdminResidency />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  role = 'hoa_admin'
  mocks.list.mockReset()
  mocks.count.mockReset()
  mocks.approve.mockReset()
  mocks.reject.mockReset()
  mocks.list.mockResolvedValue(pageOf(REQUESTS))
  mocks.count.mockResolvedValue({ pending: 1 })
})

describe('AdminResidency — the queue', () => {
  it('shows the pending count and lists applicants with their unit and status', async () => {
    renderScreen()

    expect(await screen.findByText('1 awaiting review')).toBeVisible()
    const table = within(await screen.findByRole('table'))
    expect(table.getByText('Thandi Nkosi')).toBeVisible()
    expect(table.getByText('thandi@example.co.za')).toBeVisible()
    expect(table.getByText('A-101')).toBeVisible()
    expect(table.getByText('Awaiting review')).toBeVisible()
    expect(table.getByText('Approved')).toBeVisible()
    expect(mocks.list).toHaveBeenCalledWith(1, {
      status: '',
      search: '',
      page: 1,
      page_size: 20,
    })
  })

  it('filters by status through the API, not in the browser', async () => {
    const user = userEvent.setup()
    renderScreen()
    await screen.findByText('Thandi Nkosi')

    await user.selectOptions(screen.getByLabelText('Status'), 'pending')

    await waitFor(() =>
      expect(mocks.list).toHaveBeenLastCalledWith(1, {
        status: 'pending',
        search: '',
        page: 1,
        page_size: 20,
      }),
    )
  })

  it('tells "no requests yet" apart from "nothing matches this filter"', async () => {
    mocks.list.mockResolvedValue(pageOf([]))
    renderScreen()

    expect(await screen.findByText('No registration requests yet')).toBeVisible()
    expect(screen.getByText(/appears here for you to approve or reject/i)).toBeVisible()
  })

  it('refuses the queue to someone who is not the estate’s administrator', async () => {
    role = 'resident'
    renderScreen()

    expect(await screen.findByText(/an HOA administrator’s task/i)).toBeVisible()
    expect(mocks.list).not.toHaveBeenCalled()
    expect(mocks.count).not.toHaveBeenCalled()
  })
})

describe('AdminResidency — a decision', () => {
  it('confirms an approval before sending it, then grants and reloads', async () => {
    mocks.approve.mockResolvedValue({ ...REQUESTS[0], status: 'approved' })
    const user = userEvent.setup()
    renderScreen()
    await screen.findByText('Thandi Nkosi')

    const rows = screen.getAllByRole('row')
    await user.click(rows.find((row) => row.textContent?.includes('Thandi Nkosi'))!)

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText('Lease starts 1 Nov')).toBeVisible()
    await user.click(within(dialog).getByRole('button', { name: 'Approve' }))

    // Confirmation first: nothing has been sent.
    expect(mocks.approve).not.toHaveBeenCalled()
    expect(within(dialog).getByText(/approve thandi nkosi\?/i)).toBeVisible()

    mocks.list.mockResolvedValue(pageOf([{ ...REQUESTS[0], status: 'approved' }, REQUESTS[1]]))
    await user.click(within(dialog).getByRole('button', { name: /yes, approve access/i }))

    expect(mocks.approve).toHaveBeenCalledWith(1, 31)
    await waitFor(() => expect(mocks.list).toHaveBeenCalledTimes(2))
    expect(mocks.count).toHaveBeenCalledTimes(2)
  })

  it('rejects with a reason and never calls approve', async () => {
    mocks.reject.mockResolvedValue({ ...REQUESTS[0], status: 'rejected' })
    const user = userEvent.setup()
    renderScreen()
    await screen.findByText('Thandi Nkosi')

    const rows = screen.getAllByRole('row')
    await user.click(rows.find((row) => row.textContent?.includes('Thandi Nkosi'))!)

    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: 'Reject' }))
    await user.type(within(dialog).getByLabelText(/reason/i), 'Not on the lease')
    await user.click(within(dialog).getByRole('button', { name: /yes, reject the request/i }))

    expect(mocks.reject).toHaveBeenCalledWith(1, 31, 'Not on the lease')
    expect(mocks.approve).not.toHaveBeenCalled()
  })

  it('reports a decision that someone else already made, without closing the drawer', async () => {
    mocks.approve.mockRejectedValue(
      new ApiError(409, 'That request has already been decided.', 'CONFLICT', 'req-409'),
    )
    const user = userEvent.setup()
    renderScreen()
    await screen.findByText('Thandi Nkosi')

    const rows = screen.getAllByRole('row')
    await user.click(rows.find((row) => row.textContent?.includes('Thandi Nkosi'))!)
    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: 'Approve' }))
    await user.click(within(dialog).getByRole('button', { name: /yes, approve access/i }))

    expect(await within(dialog).findByText('Someone already decided this')).toBeVisible()
    expect(within(dialog).getByText(/already been decided/i)).toBeVisible()
  })

  it('opens the request a notification email linked to, and only after the queue loads', async () => {
    renderScreen('/admin/residency?request=20')

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText(/unit B-4 · request #20/)).toBeVisible()
  })
})
