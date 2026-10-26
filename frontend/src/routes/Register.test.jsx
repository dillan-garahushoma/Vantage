/** Public account paths are visible; only resident self-registration creates an account. */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { registrationPayload, Register } from './Register';

const mocks = vi.hoisted(() => ({
  register: vi.fn(),
  registerEstate: vi.fn(),
  logout: vi.fn(),
  listPublic: vi.fn(),
}));
vi.mock('../lib/publicDirectory', () => ({ listPublicEstates: mocks.listPublic }));
vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    register: mocks.register,
    registerEstate: mocks.registerEstate,
    logout: mocks.logout,
  }),
}));

beforeEach(() => {
  mocks.register.mockReset();
  mocks.registerEstate.mockReset();
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
  it('requires an HOA manager to choose the province instead of assuming a location', async () => {
    const user = userEvent.setup();
    renderRegister();
    await user.click(screen.getByRole('radio', { name: /hoa \/ estate manager/i }));
    await user.type(screen.getByRole('textbox', { name: /your full name/i }), 'Lerato Mokoena');
    await user.type(screen.getByRole('textbox', { name: /email address/i }), 'lerato@example.co.za');
    await user.type(screen.getByLabelText(/password/i), 'aGoodPassword1');
    await user.click(screen.getByRole('button', { name: /continue to estate details/i }));
    await user.type(screen.getByRole('textbox', { name: /estate name/i }), 'Ridge Close');
    await user.type(screen.getByRole('textbox', { name: /suburb/i }), 'Centurion');
    await user.type(screen.getByRole('textbox', { name: /city/i }), 'Tshwane');
    expect(screen.getByRole('combobox', { name: /^Province/ })).toHaveValue('');
    await user.click(screen.getByRole('button', { name: /review estate details/i }));
    expect(screen.getByText('Choose a province.')).toBeVisible();
  });
  it('shows resident, HOA manager and service provider account paths', () => {
    renderRegister();
    expect(screen.getByRole('radio', { name: /^resident/i })).toBeChecked();
    expect(screen.getByRole('radio', { name: /hoa \/ estate manager/i })).toBeVisible();
    expect(screen.getByRole('radio', { name: /service provider/i })).toBeVisible();
  });

  it('offers direct HOA estate onboarding without requiring operator provisioning', async () => {
    const user = userEvent.setup();
    renderRegister();
    await user.click(screen.getByRole('radio', { name: /hoa \/ estate manager/i }));
    expect(screen.getByRole('navigation', { name: /estate setup progress/i })).toBeVisible();
    expect(screen.getByRole('textbox', { name: /your full name/i })).toBeVisible();
    expect(screen.queryByRole('textbox', { name: /estate name/i })).toBeNull();

    await user.click(screen.getByRole('radio', { name: /service provider/i }));
    expect(screen.getByRole('link', { name: /apply to work at an estate/i })).toBeVisible();
  });

  it('creates the HOA account and estate through the public estate-registration contract', async () => {
    mocks.registerEstate.mockResolvedValue({});
    const user = userEvent.setup();
    renderRegister();
    await user.click(screen.getByRole('radio', { name: /hoa \/ estate manager/i }));
    await user.type(screen.getByRole('textbox', { name: /your full name/i }), 'Lerato Mokoena');
    await user.type(screen.getByRole('textbox', { name: /email address/i }), 'lerato@example.co.za');
    await user.type(screen.getByLabelText(/password/i), 'aGoodPassword1');
    await user.click(screen.getByRole('button', { name: /continue to estate details/i }));
    await user.type(screen.getByRole('textbox', { name: /estate name/i }), 'Ridge Close');
    await user.type(screen.getByRole('textbox', { name: /suburb/i }), 'Centurion');
    await user.type(screen.getByRole('textbox', { name: /city/i }), 'Tshwane');
    await user.selectOptions(screen.getByRole('combobox', { name: /^Province/ }), 'Gauteng');
    await user.click(screen.getByRole('button', { name: /review estate details/i }));
    expect(screen.getByRole('heading', { name: /review and create/i })).toBeVisible();
    expect(screen.getByText('Ridge Close')).toBeVisible();
    expect(screen.getByText('lerato@example.co.za')).toBeVisible();
    await user.click(screen.getByRole('button', { name: /create estate and hoa account/i }));

    expect(mocks.registerEstate).toHaveBeenCalledWith({
      full_name: 'Lerato Mokoena',
      email: 'lerato@example.co.za',
      password: 'aGoodPassword1',
      estate: {
        name: 'Ridge Close',
        suburb: 'Centurion',
        city: 'Tshwane',
        province: 'Gauteng',
      },
    });
    expect(mocks.register).not.toHaveBeenCalled();
  }, 30000);

  it('validates each step and preserves account details when moving back', async () => {
    const user = userEvent.setup();
    renderRegister();
    await user.click(screen.getByRole('radio', { name: /hoa \/ estate manager/i }));
    await user.click(screen.getByRole('button', { name: /continue to estate details/i }));
    expect(await screen.findByText('Enter your full name.')).toBeVisible();
    expect(screen.queryByRole('textbox', { name: /estate name/i })).toBeNull();

    await user.type(screen.getByRole('textbox', { name: /your full name/i }), 'Lerato Mokoena');
    await user.type(screen.getByRole('textbox', { name: /email address/i }), 'lerato@example.co.za');
    await user.type(screen.getByLabelText(/password/i), 'aGoodPassword1');
    await user.click(screen.getByRole('button', { name: /continue to estate details/i }));
    await user.type(screen.getByRole('textbox', { name: /estate name/i }), 'Ridge Close');
    await user.click(screen.getByRole('button', { name: /review estate details/i }));
    expect(await screen.findByText('Enter the suburb.')).toBeVisible();

    await user.type(screen.getByRole('textbox', { name: /suburb/i }), 'Centurion');
    await user.type(screen.getByRole('textbox', { name: /city/i }), 'Tshwane');
    await user.selectOptions(screen.getByRole('combobox', { name: /^Province/ }), 'Gauteng');
    await user.click(screen.getByRole('button', { name: /review estate details/i }));
    await user.click(screen.getByRole('button', { name: /edit account details/i }));
    expect(screen.getByRole('textbox', { name: /your full name/i })).toHaveValue('Lerato Mokoena');
    expect(screen.getByRole('textbox', { name: /email address/i })).toHaveValue('lerato@example.co.za');
  });

  it('restores resident registration when the resident path is selected again', async () => {
    const user = userEvent.setup();
    renderRegister();
    await user.click(screen.getByRole('radio', { name: /hoa \/ estate manager/i }));
    await user.click(screen.getByRole('radio', { name: /^resident/i }));
    expect(screen.getByRole('button', { name: /continue to estate/i })).toBeVisible();
    expect(screen.getByRole('textbox', { name: /full name/i })).toBeVisible();
  });
});


describe('Register — estate discovery and context', () => {
  it('loads published estates from the directory endpoint and lets a resident select one', async () => {
    const user = userEvent.setup();
    renderRegister();
    await user.type(screen.getByRole('textbox', { name: /full name/i }), 'Thandi Nkosi');
    await user.type(screen.getByRole('textbox', { name: /email address/i }), 'thandi@example.co.za');
    await user.type(screen.getByLabelText(/password/i), 'aGoodPassword1');
    await user.click(screen.getByRole('button', { name: /continue to estate/i }));

    expect(await screen.findByRole('button', { name: /ridge close estate/i })).toBeVisible();
    expect(mocks.listPublic).toHaveBeenCalledWith({ q: '', page: 1, page_size: 6 });

    await user.click(screen.getByRole('button', { name: /silverleaf reserve/i }));
    expect(screen.getByText('Silverleaf Reserve')).toBeVisible();
    expect(screen.getByText(/you can request access after creating your account/i)).toBeVisible();
  });

  it('lets a resident create an account and request access without a unit number', async () => {
    mocks.register.mockResolvedValue({});
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
    await user.type(screen.getByRole('textbox', { name: /full name/i }), 'Thandi Nkosi');
    await user.type(screen.getByRole('textbox', { name: /email address/i }), 'thandi@example.co.za');
    await user.type(screen.getByLabelText(/password/i), 'aGoodPassword1');
    await user.click(screen.getByRole('button', { name: /continue to estate/i }));

    await user.clear(screen.getByRole('textbox', { name: /search published complexes/i }));
    await user.type(screen.getByRole('textbox', { name: /search published complexes/i }), 'Ridge');
    await user.click(screen.getByRole('button', { name: /^search$/i }));
    await user.click(await screen.findByRole('button', { name: /ridge close estate/i }));
    await user.click(screen.getByRole('button', { name: /review details/i }));
    await user.click(screen.getByRole('button', { name: /create account/i }));

    expect(screen.queryByRole('textbox', { name: /unit number/i })).toBeNull();
    expect(mocks.register).toHaveBeenCalledWith({
      full_name: 'Thandi Nkosi',
      email: 'thandi@example.co.za',
      password: 'aGoodPassword1',
      account_type: 'resident',
    });
    expect(JSON.parse(window.sessionStorage.getItem('valora.public-estate-selection'))).toMatchObject({
      estate_id: 4,
      name: 'Ridge Close Estate',
    });
  });

  it('keeps only the selected estate as access-request context, never a unit in signup', async () => {
    mocks.register.mockResolvedValue({});
    const user = userEvent.setup();
    renderRegister();
    await user.type(screen.getByRole('textbox', { name: /full name/i }), 'Thandi Nkosi');
    await user.type(screen.getByRole('textbox', { name: /email address/i }), 'thandi@example.co.za');
    await user.type(screen.getByLabelText(/password/i), 'aGoodPassword1');
    await user.click(screen.getByRole('button', { name: /continue to estate/i }));
    await user.click(await screen.findByRole('button', { name: /ridge close estate/i }));
    await user.click(screen.getByRole('button', { name: /review details/i }));
    await user.click(screen.getByRole('button', { name: /create account/i }));

    expect(mocks.register).toHaveBeenCalledWith({
      full_name: 'Thandi Nkosi',
      email: 'thandi@example.co.za',
      password: 'aGoodPassword1',
      account_type: 'resident',
    });
    expect(JSON.parse(window.sessionStorage.getItem('valora.public-estate-selection'))).toMatchObject({
      estate_id: 4,
      name: 'Ridge Close Estate',
    });
  });
});
