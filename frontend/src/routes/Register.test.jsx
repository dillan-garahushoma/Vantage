/** Public account paths are visible; only resident self-registration creates an account. */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { registrationPayload, Register } from './Register';

const mocks = vi.hoisted(() => ({ register: vi.fn(), logout: vi.fn() }));
vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: null, register: mocks.register, logout: mocks.logout }),
}));

beforeEach(() => {
  mocks.register.mockReset();
  mocks.logout.mockReset();
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
    expect(screen.getByRole('radio', { name: /^resident\b/i })).toBeChecked();
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
    await user.click(screen.getByRole('radio', { name: /^resident\b/i }));
    expect(screen.getByRole('button', { name: /create resident account/i })).toBeVisible();
    expect(screen.getByRole('textbox', { name: /full name/i })).toBeVisible();
  });
});
