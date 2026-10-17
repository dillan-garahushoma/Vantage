/**
 * The estate register.
 *
 * Removal is the screen's one destructive action, so the test pins the promise it
 * makes: it is confirmed, it names what it does *not* undo (the account, the
 * history, and any live join code), and a rejected removal is shown as the
 * server's own message rather than swallowed.
 */
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../lib/api'
import { Members } from './Members'

const mocks = vi.hoisted(() => ({
  list: vi.fn(),
  remove: vi.fn(),
  addProvider: vi.fn(),
}))

vi.mock('../lib/estateAdmin', () => ({
  listEstateMembers: mocks.list,
  removeEstateMember: mocks.remove,
  addProviderMember: mocks.addProvider,
}))

let role: string | null = 'hoa_admin'

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, full_name: 'Nomvula Dlamini', role } }),
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

function pageOf(items: unknown[]) {
  return { items, total: items.length, page: 1, size: 20, pages: 1 }
}

const MEMBERS = [
  {
    membership_id: 11,
    role: 'resident',
    full_name: 'Thandi Nkosi',
    email: 'thandi@example.co.za',
    unit_no: 'A-101',
    joined_at: '2026-09-02T08:00:00Z',
  },
  {
    membership_id: 12,
    role: 'service_provider',
    full_name: 'Sipho Mokoena',
    email: 'sipho@example.co.za',
    unit_no: null,
    joined_at: '2026-09-14T08:00:00Z',
  },
  {
    membership_id: 13,
    role: 'hoa_admin',
    full_name: 'Nomvula Dlamini',
    email: 'nomvula@example.co.za',
    unit_no: 'A-1',
    joined_at: '2026-08-01T08:00:00Z',
  },
]

function renderMembers() {
  return render(
    <MemoryRouter>
      <Members />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  role = 'hoa_admin'
  mocks.list.mockReset()
  mocks.remove.mockReset()
  mocks.addProvider.mockReset()
  mocks.list.mockResolvedValue(pageOf(MEMBERS))
})

describe('Members — the register', () => {
  it('lists members with their role, unit and joining date', async () => {
    renderMembers()

    const table = within(await screen.findByRole('table'))
    expect(table.getByText('Thandi Nkosi')).toBeVisible()
    expect(table.getByText('thandi@example.co.za')).toBeVisible()
    expect(table.getByText('A-101')).toBeVisible()
    expect(table.getByText('Sipho Mokoena')).toBeVisible()
    // Scoped to the table: the role filter offers the same words as options.
    expect(table.getByText('Service provider')).toBeVisible()
    expect(table.getByText('HOA administrator')).toBeVisible()
    expect(mocks.list).toHaveBeenCalledWith(1, { role: undefined, page: 1, page_size: 20 })
  })

  it('says how people get in, naming both approvals and join codes', async () => {
    renderMembers()

    expect((await screen.findAllByText(/approved on the approvals screen/i)).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/join code against their unit number/i).length).toBeGreaterThan(0)
  })

  it('offers removal for members but not for the estate’s administrators', async () => {
    renderMembers()
    await screen.findByText('Thandi Nkosi')

    const rows = screen.getAllByRole('row')
    const resident = rows.find((row) => row.textContent?.includes('Thandi Nkosi'))
    const admin = rows.find((row) => row.textContent?.includes('Nomvula Dlamini'))

    expect(within(resident!).getByRole('button', { name: 'Remove' })).toBeVisible()
    expect(within(admin!).queryByRole('button', { name: 'Remove' })).toBeNull()
    expect(within(admin!).getByText(/remove from the estate profile/i)).toBeVisible()
  })

  it('filters by role through the API, not in the browser', async () => {
    const user = userEvent.setup()
    renderMembers()
    await screen.findByText('Thandi Nkosi')

    await user.selectOptions(screen.getByLabelText('Role'), 'service_provider')

    await waitFor(() =>
      expect(mocks.list).toHaveBeenLastCalledWith(1, {
        role: 'service_provider',
        page: 1,
        page_size: 20,
      }),
    )
  })

  it('distinguishes "nobody holds this role" from "no members at all"', async () => {
    mocks.list.mockResolvedValue(pageOf([]))
    renderMembers()

    expect(await screen.findByText('This estate has no members yet')).toBeVisible()
    expect(screen.getByText(/issue a join code/i)).toBeVisible()
  })

  it('shows a rejected read with its reference and a retry', async () => {
    mocks.list.mockRejectedValue(
      new ApiError(403, 'You do not have permission to perform this action.', 'FORBIDDEN', 'req-403'),
    )
    renderMembers()

    expect(await screen.findByText(/could not read the estate register/i)).toBeVisible()
    expect(screen.getByText(/req-403/)).toBeVisible()

    mocks.list.mockResolvedValue(pageOf(MEMBERS))
    await userEvent.setup().click(screen.getByRole('button', { name: /try again/i }))
    expect(await screen.findByText('Thandi Nkosi')).toBeVisible()
  })

  it('refuses the register to someone who is not the estate’s administrator', async () => {
    role = 'resident'
    renderMembers()

    expect(await screen.findByText(/an HOA administrator’s view/i)).toBeVisible()
    expect(mocks.list).not.toHaveBeenCalled()
  })
})

describe('Members — removal', () => {
  it('confirms first, and spells out what removal does not undo', async () => {
    const user = userEvent.setup()
    renderMembers()
    await screen.findByText('Thandi Nkosi')

    const rows = screen.getAllByRole('row')
    const resident = rows.find((row) => row.textContent?.includes('Thandi Nkosi'))
    await user.click(within(resident!).getByRole('button', { name: 'Remove' }))

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText(/ends their access to/i)).toBeVisible()
    expect(within(dialog).getByText(/does not delete their account/i)).toBeVisible()
    expect(within(dialog).getByText(/complaints they filed/i)).toBeVisible()
    expect(within(dialog).getByText(/does not cancel a join code/i)).toBeVisible()
    expect(mocks.remove).not.toHaveBeenCalled()
  })

  it('removes on confirmation and reloads the register', async () => {
    mocks.remove.mockResolvedValue(undefined)
    const user = userEvent.setup()
    renderMembers()
    await screen.findByText('Thandi Nkosi')

    const rows = screen.getAllByRole('row')
    const resident = rows.find((row) => row.textContent?.includes('Thandi Nkosi'))
    await user.click(within(resident!).getByRole('button', { name: 'Remove' }))
    await user.click(await screen.findByRole('button', { name: /remove from the estate/i }))

    expect(mocks.remove).toHaveBeenCalledWith(1, 11)
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    expect(mocks.list).toHaveBeenCalledTimes(2)
  })

  it('keeps the member when the confirmation is dismissed', async () => {
    const user = userEvent.setup()
    renderMembers()
    await screen.findByText('Thandi Nkosi')

    const rows = screen.getAllByRole('row')
    const resident = rows.find((row) => row.textContent?.includes('Thandi Nkosi'))
    await user.click(within(resident!).getByRole('button', { name: 'Remove' }))
    await user.click(await screen.findByRole('button', { name: /keep the member/i }))

    expect(mocks.remove).not.toHaveBeenCalled()
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  })

  it('reports a rejected removal inside the dialog, without closing it', async () => {
    mocks.remove.mockRejectedValue(
      new ApiError(404, 'Membership not found in this estate.', 'RESOURCE_NOT_FOUND', 'req-404'),
    )
    const user = userEvent.setup()
    renderMembers()
    await screen.findByText('Thandi Nkosi')

    const rows = screen.getAllByRole('row')
    const resident = rows.find((row) => row.textContent?.includes('Thandi Nkosi'))
    await user.click(within(resident!).getByRole('button', { name: 'Remove' }))
    await user.click(await screen.findByRole('button', { name: /remove from the estate/i }))

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText(/membership not found in this estate/i)).toBeVisible()
    expect(within(dialog).getByText(/req-404/)).toBeVisible()
  })
})

describe('Members — adding a provider', () => {
  it('explains a 404 as "they must register first", and that residents cannot be added here', async () => {
    mocks.addProvider.mockRejectedValue(
      new ApiError(404, 'No registered service provider with that email.', 'RESOURCE_NOT_FOUND'),
    )
    const user = userEvent.setup()
    renderMembers()
    await screen.findByText('Thandi Nkosi')

    await user.type(screen.getByLabelText(/provider email/i), 'nobody@example.co.za')
    await user.click(screen.getByRole('button', { name: /add provider/i }))

    expect(await screen.findByText(/no registered provider with that email/i)).toBeVisible()
    expect(screen.getByText(/must first create their own VALORA account/i)).toBeVisible()
    expect(screen.getByText(/residents are not added here/i)).toBeVisible()
  })

  it('adds a provider by email and reports it in the estate’s terms', async () => {
    mocks.addProvider.mockResolvedValue({
      membership_id: 21,
      role: 'service_provider',
      full_name: 'Sipho Mokoena',
      email: 'sipho@example.co.za',
      unit_no: null,
      joined_at: '2026-10-12T08:00:00Z',
    })
    const user = userEvent.setup()
    renderMembers()
    await screen.findByText('Thandi Nkosi')

    await user.type(screen.getByLabelText(/provider email/i), 'sipho@example.co.za')
    await user.click(screen.getByRole('button', { name: /add provider/i }))

    expect(mocks.addProvider).toHaveBeenCalledWith(1, 'sipho@example.co.za')
    expect(
      await screen.findByText(/can now be assigned work in this estate/i),
    ).toBeVisible()
    expect(mocks.list).toHaveBeenCalledTimes(2)
  })
})
