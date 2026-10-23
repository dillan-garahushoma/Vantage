/** Public account paths are visible; only resident self-registration creates an account. */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { registrationPayload, Register } from './Register';

const mocks = vi.hoisted(() => ({ register: vi.fn(), logout: vi.fn(), listPublic: vi.fn() }));
vi.mock('../lib/publicDirectory', () => ({ listPublicEstates: mocks.listPublic }));
vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: null, register: mocks.register, logout: mocks.logout }),
}));

beforeEach(() => {
  mocks.register.mockReset();
  mocks.logout.mockReset();
  mocks.listPublic.mockReset();
  mocks.listPublic.mockResolvedValue({
    items: [
      { estate_id: 4, name: 'Ridge Close Estate', suburb: 'Centurion', city: 'Tshwane', province: 'Gauteng', unit_count: 24 },
      { estate_id: 5, name: 'Silverleaf Reserve', suburb: 'Constantia', city: 'Cape Town', province: 'Western Cape', unit_count: 40 },
    ],
    total: 2,
    page: 1,
    size: 6,
    pages: 1,
  });
  window.sessionStorage.clear();
});

function renderRegister() {
  return render(<MemoryRouter><Register /></MemoryRouter>);
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
};

describe('registrationPayload', () => {
  it('sends a resident request with no estate and no provider', () => {
    const payload = registrationPayload({ ...BASE });
    expect(payload.account_type).toBe('resident');
    expect(payload).toEqual({
      full_name: 'Thandi Nkosi',
      email: 'thandi@example.co.za',
      password: 'aGoodPassword1',
      phoneno: '082 000 0000',
      account_type: 'resident',
      unit_no: 'A-101',
    });
    expect(payload).not.toHaveProperty('estate');
    expect(payload).not.toHaveProperty('provider');
  });

  it('omits optional strings instead of sending empty ones', () => {
    const payload = registrationPayload({ ...BASE, phoneno: '   ', unit_no: '', estateDescription: '  ' });
    expect(payload).not.toHaveProperty('phoneno');
    expect(payload).not.toHaveProperty('unit_no');
  });

  it('never turns a trusted-account UI choice into a privileged registration payload', () => {
    for (const accountType of ['estate_admin', 'service_provider']) {
      const payload = registrationPayload({ ...BASE, accountType });
      expect(payload.account_type).toBe('resident');
      expect(payload).not.toHaveProperty('role');
      expect(payload).not.toHaveProperty('estate');
      expect(payload).not.toHaveProperty('provider');
    }
  });
});

describe('Register — role paths and safe permissions', () => {
  it('shows resident, HOA manager and service provider account paths', () => {
    renderRegister();
    expect(screen.getByRole('radio', { name: /^resident/i })).toBeChecked();
    expect(screen.getByRole('radio', { name: /hoa \/ estate manager/i })).toBeVisible();
    expect(screen.getByRole('radio', { name: /service provider/i })).toBeVisible();
  });

  it('explains trusted provisioning rather than granting elevated roles', async () => {
    const user = userEvent.setup();
    renderRegister();
    await user.click(screen.getByRole('radio', { name: /hoa \/ estate manager/i }));
    expect(screen.getByText(/must be provisioned and attached to its estate/i)).toBeVisible();
    expect(screen.getByRole('link', { name: /contact valora/i })).toBeVisible();
    expect(screen.queryByRole('button', { name: /create resident account/i })).toBeNull();

    await user.click(screen.getByRole('radio', { name: /service provider/i }));
    expect(screen.getByText(/linked to an approved provider profile and estate membership/i)).toBeVisible();
    expect(screen.queryByRole('button', { name: /create resident account/i })).toBeNull();
  });

  it('restores resident registration when the resident path is selected again', async () => {
    const user = userEvent.setup();
    renderRegister();
    await user.click(screen.getByRole('radio', { name: /hoa \/ estate manager/i }));
    await user.click(screen.getByRole('radio', { name: /^resident/i }));
    expect(screen.getByRole('button', { name: /create resident account/i })).toBeVisible();
    expect(screen.getByRole('textbox', { name: /full name/i })).toBeVisible();
  });
});


describe('Register — estate discovery and context', () => {
  it('loads published estates from the directory endpoint and lets a resident select one', async () => {
    const user = userEvent.setup();
    renderRegister();

    expect(await screen.findByRole('button', { name: /ridge close estate/i })).toBeVisible();
    expect(mocks.listPublic).toHaveBeenCalledWith({ q: '', page: 1, page_size: 6 });

    await user.click(screen.getByRole('button', { name: /silverleaf reserve/i }));
    expect(screen.getByText('Silverleaf Reserve')).toBeVisible();
    expect(screen.getByText(/you will confirm your unit and request access after creating your account/i)).toBeVisible();
  });

  it('searches the public directory and requires a unit when the resident picked a complex', async () => {
    mocks.listPublic.mockImplementation(async ({ q }) => ({
      items: q.toLowerCase().includes('ridge')
        ? [{ estate_id: 4, name: 'Ridge Close Estate', suburb: 'Centurion', city: 'Tshwane', province: 'Gauteng', unit_count: 24 }]
        : [],
      total: q.toLowerCase().includes('ridge') ? 1 : 0,
      page: 1,
      size: 6,
      pages: 1,
    }));
    const user = userEvent.setup();
    renderRegister();

    await user.clear(screen.getByRole('textbox', { name: /search published complexes/i }));
    await user.type(screen.getByRole('textbox', { name: /search published complexes/i }), 'Ridge');
    await user.click(screen.getByRole('button', { name: /^search$/i }));
    await user.click(await screen.findByRole('button', { name: /ridge close estate/i }));

    await user.type(screen.getByRole('textbox', { name: /full name/i }), 'Thandi Nkosi');
    await user.type(screen.getByRole('textbox', { name: /email address/i }), 'thandi@example.co.za');
    await user.type(screen.getByLabelText(/password/i), 'aGoodPassword1');
    await user.click(screen.getByRole('button', { name: /create resident account/i }));

    expect(await screen.findByText(/enter the unit number for the complex you selected/i)).toBeVisible();
    expect(mocks.register).not.toHaveBeenCalled();
  });

  it('keeps estate and unit as onboarding context, not an authorization field in the account payload', async () => {
    mocks.register.mockResolvedValue({});
    const user = userEvent.setup();
    renderRegister();

    await user.click(await screen.findByRole('button', { name: /ridge close estate/i }));
    await user.type(screen.getByRole('textbox', { name: /full name/i }), 'Thandi Nkosi');
    await user.type(screen.getByRole('textbox', { name: /email address/i }), 'thandi@example.co.za');
    await user.type(screen.getByLabelText(/password/i), 'aGoodPassword1');
    await user.type(screen.getByRole('textbox', { name: /unit number/i }), ' A-101 ');
    await user.click(screen.getByRole('button', { name: /create resident account/i }));

    expect(mocks.register).toHaveBeenCalledWith({
      full_name: 'Thandi Nkosi',
      email: 'thandi@example.co.za',
      password: 'aGoodPassword1',
      account_type: 'resident',
      unit_no: 'A-101',
    });
    expect(JSON.parse(window.sessionStorage.getItem('valora.public-estate-selection'))).toMatchObject({
      estate_id: 4,
      name: 'Ridge Close Estate',
      unit_no: 'A-101',
    });
  });
});
