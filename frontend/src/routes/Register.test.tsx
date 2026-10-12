/**
 * Registration's one job: send the request the chosen account type requires.
 *
 * The API rejects a `role` field outright and requires an `estate` object for an
 * administrator and a `provider` object for a provider, so these tests pin the
 * exact body — including the absence of the objects the API would refuse.
 */
import { describe, expect, it } from 'vitest'

import { registrationPayload } from './Register'

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
