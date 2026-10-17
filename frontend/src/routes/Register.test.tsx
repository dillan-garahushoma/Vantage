/**
 * Registration's one job: send the request the chosen account type requires.
 *
 * The API rejects a `role` field outright and requires an `estate` object for an
 * administrator and a `provider` object for a provider, so these tests pin the
 * exact body — including the absence of the objects the API would refuse.
 *
 * It also pins how the choice is *made*, because that is where the screen failed:
 * the three cards look like one clickable control but only the 16px radio and the
 * label text responded, so a person clicking the card — or its description, the
 * part that explains what they are choosing — got nothing.
 */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { registrationPayload, Register } from './Register'

const mocks = vi.hoisted(() => ({ register: vi.fn() }))

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: null, register: mocks.register }),
}))

beforeEach(() => {
  mocks.register.mockReset()
})

function renderRegister() {
  return render(
    <MemoryRouter>
      <Register />
    </MemoryRouter>,
  )
}


const BASE = {
  accountType: 'resident',
  full_name: '  Thandi Nkosi  ',
  email: '  thandi@example.co.za ',
  password: 'aGoodPassword1',
  phoneno: '  082 000 0000 ',
  unit_no: ' A-101 ',
  estateName: ' Ridge Close Estate ',
  estateSuburb: ' Centurion ',
  estateCity: ' Tshwane ',
  estateProvince: 'Gauteng',
  estateDescription: ' A 24-unit complex. ',
  trade: ' plumbing ',
  providerPhone: ' 082 000 0000 ',
} as const

describe('registrationPayload', () => {
  it('sends a resident request with no estate and no provider', () => {
    const payload = registrationPayload({ ...BASE })

    expect(payload.account_type).toBe('resident')
    expect(payload).toEqual({
      full_name: 'Thandi Nkosi',
      email: 'thandi@example.co.za',
      password: 'aGoodPassword1',
      phoneno: '082 000 0000',
      account_type: 'resident',
      unit_no: 'A-101',
    })
    expect(payload).not.toHaveProperty('estate')
    expect(payload).not.toHaveProperty('provider')
  })

  it('sends the estate with an administrator, and no provider object', () => {
    const payload = registrationPayload({ ...BASE, accountType: 'estate_admin' })

    expect(payload.account_type).toBe('estate_admin')
    expect(payload.estate).toEqual({
      name: 'Ridge Close Estate',
      suburb: 'Centurion',
      city: 'Tshwane',
      province: 'Gauteng',
      description: 'A 24-unit complex.',
    })
    expect(payload).not.toHaveProperty('provider')
    // The unit the resident typed is a resident field: it must not travel here.
    expect(payload).not.toHaveProperty('unit_no')
  })

  it('sends the trade and phone with a provider, and no estate object', () => {
    const payload = registrationPayload({ ...BASE, accountType: 'service_provider' })

    expect(payload.account_type).toBe('service_provider')
    expect(payload.provider).toEqual({ trade: 'plumbing', phone: '082 000 0000' })
    expect(payload).not.toHaveProperty('estate')
    expect(payload).not.toHaveProperty('unit_no')
  })

  it('omits optional strings instead of sending empty ones', () => {
    const payload = registrationPayload({
      ...BASE,
      phoneno: '   ',
      unit_no: '',
      estateDescription: '  ',
    })

    expect(payload).not.toHaveProperty('phoneno')
    expect(payload).not.toHaveProperty('unit_no')

    const admin = registrationPayload({
      ...BASE,
      accountType: 'estate_admin',
      estateDescription: '',
    })
    expect(admin.estate).not.toHaveProperty('description')
  })

  it('never sends a role, whoever is registering', () => {
    for (const accountType of ['resident', 'estate_admin', 'service_provider'] as const) {
      const payload = registrationPayload({ ...BASE, accountType })
      expect(payload, accountType).not.toHaveProperty('role')
      expect(JSON.stringify(payload), accountType).not.toContain('"role"')
    }
  })
})

describe('Register — choosing the account type', () => {
  it('chooses the type that was clicked, from the radio, the title or the description', async () => {
    const user = userEvent.setup()
    renderRegister()

    await user.click(screen.getByRole('radio', { name: 'Service provider' }))
    expect(screen.getByRole('heading', { name: /service provider account/i })).toBeVisible()

    // The title is a second way in.
    await user.click(screen.getByText('Estate administrator'))
    expect(screen.getByRole('heading', { name: /estate administrator account/i })).toBeVisible()

    // And the description — the part that explains what is being chosen, and the
    // most natural thing to click — must choose it too.
    await user.click(screen.getByText(/do the work/i))
    expect(screen.getByRole('heading', { name: /service provider account/i })).toBeVisible()
    expect(screen.getByLabelText(/^trade/i)).toBeVisible()
  })

  it('fills the card, not just its text, as the click target', async () => {
    const user = userEvent.setup()
    renderRegister()

    // A click in the card's empty space — below the description, inside the
    // border — is still a click on the choice.
    const card = screen.getByText(/register the estate you manage/i).closest('label')
    expect(card).not.toBeNull()
    await user.click(card!)

    expect(screen.getByRole('heading', { name: /estate administrator account/i })).toBeVisible()
    expect(screen.getByLabelText(/estate name/i)).toBeVisible()
  })

  it('names each radio by its account type and describes it by its blurb', async () => {
    renderRegister()

    const radio = screen.getByRole('radio', { name: 'Resident' })
    expect(radio).toBeChecked()
    // The explanation belongs to the control, but not inside its name: a screen
    // reader should hear “Resident”, then what that means.
    expect(radio).toHaveAccessibleDescription(/join with a code from your estate office/i)
  })

  it('moves the choice with the arrow keys', async () => {
    const user = userEvent.setup()
    renderRegister()

    screen.getByRole('radio', { name: 'Resident' }).focus()
    await user.keyboard('{ArrowDown}')

    expect(screen.getByRole('radio', { name: 'Estate administrator' })).toBeChecked()
    expect(screen.getByRole('heading', { name: /estate administrator account/i })).toBeVisible()
  })
})
