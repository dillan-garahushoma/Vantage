/**
 * Redeeming a join code.
 *
 * The screen must not name an estate it was not told about, must not turn a
 * uniform 404 into a guess about which estate exists, and must check the two
 * fields before spending one of the five rate-limited attempts.
 */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import { ApiError } from '../lib/api'
import { Join } from './Join'

// `vi.hoisted` so the mock factories can share these, and so the test body can
// still assert on them: a `vi.mock` factory is hoisted above ordinary imports.
const mocks = vi.hoisted(() => ({ join: vi.fn(), reload: vi.fn() }))

vi.mock('../lib/estateAdmin', () => ({ joinEstateWithCode: mocks.join }))

vi.mock('../context/EstateContext', () => ({
  useEstate: () => ({
    estates: [],
    reload: mocks.reload,
    loading: false,
    error: null,
    awaitingProvisioning: false,
  }),
}))

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, full_name: 'Thandi Nkosi', role: 'resident' } }),
}))

function renderJoin() {
  return render(
    <MemoryRouter initialEntries={['/join']}>
      <Routes>
        <Route path="/join" element={<Join />} />
        <Route path="/app" element={<p>dashboard</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  mocks.join.mockReset()
  mocks.reload.mockReset()
})

describe('Join', () => {
  it('states that the code names the estate, so the person cannot type one in', () => {
    renderJoin()

    expect(screen.getByRole('heading', { level: 1, name: /enter your code and unit/i })).toBeVisible()
    expect(screen.getByText(/it names the estate for you/i)).toBeVisible()
  })

  it('checks both fields before spending one of the five attempts', async () => {
    const user = userEvent.setup()
    renderJoin()

    await user.click(screen.getByRole('button', { name: /join the estate/i }))

    expect(await screen.findByText(/enter the code your estate office gave you/i)).toBeVisible()
    expect(screen.getByText(/enter your unit number/i)).toBeVisible()
    expect(mocks.join).not.toHaveBeenCalled()
  })

  it('submits the trimmed code and unit, then reloads the estate scope', async () => {
    mocks.join.mockResolvedValue({
      estate_id: 1,
      estate_name: 'Ridge Close',
      unit_id: 10,
      unit_no: 'A-101',
      role: 'resident',
    })
    const user = userEvent.setup()
    renderJoin()

    await user.type(screen.getByLabelText(/join code/i), ' abcd2efgh3 ')
    await user.type(screen.getByLabelText(/unit number/i), ' A-101 ')
    await user.click(screen.getByRole('button', { name: /join the estate/i }))

    expect(mocks.join).toHaveBeenCalledWith('abcd2efgh3', 'A-101')
    expect(await screen.findByText('dashboard')).toBeVisible()
    expect(mocks.reload).toHaveBeenCalledTimes(1)
  })

  it('reports an unusable code as unusable, without naming any estate', async () => {
    mocks.join.mockRejectedValue(
      new ApiError(404, 'That join code is not valid for any estate.', 'RESOURCE_NOT_FOUND', 'req-404'),
    )
    const user = userEvent.setup()
    renderJoin()

    await user.type(screen.getByLabelText(/join code/i), 'WRONGCODE1')
    await user.type(screen.getByLabelText(/unit number/i), 'A-101')
    await user.click(screen.getByRole('button', { name: /join the estate/i }))

    expect(await screen.findByText(/that join code is not valid for any estate/i)).toBeVisible()
    expect(screen.getByText(/req-404/)).toBeVisible()
    expect(mocks.reload).not.toHaveBeenCalled()
  })

  it('explains the rate limit in the estate office’s own terms', async () => {
    mocks.join.mockRejectedValue(
      new ApiError(429, 'Too many join attempts. Try again in a few minutes.', 'RATE_LIMITED'),
    )
    const user = userEvent.setup()
    renderJoin()

    await user.type(screen.getByLabelText(/join code/i), 'WRONGCODE1')
    await user.type(screen.getByLabelText(/unit number/i), 'A-101')
    await user.click(screen.getByRole('button', { name: /join the estate/i }))

    expect(await screen.findByText('Too many attempts')).toBeVisible()
    expect(screen.getByText(/try again in a few minutes/i)).toBeVisible()
  })
})
