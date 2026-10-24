import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { estateOnboardingPayload, registrationPayload, Register } from './Register';

const auth = vi.hoisted(() => ({
  user: null,
  logout: vi.fn(),
  register: vi.fn(),
  registerEstate: vi.fn(),
}));

vi.mock('../context/AuthContext', () => ({
  useAuth: () => auth,
}));

beforeEach(() => {
  auth.user = null;
  vi.clearAllMocks();
});

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
};

function renderRegister() {
  return render(
    <MemoryRouter>
      <Register />
    </MemoryRouter>,
  );
}

describe('registration payloads', () => {
  it('keeps public resident registration limited to resident data', () => {
    expect(registrationPayload(BASE)).toEqual({
      full_name: 'Thandi Nkosi',
      email: 'thandi@example.co.za',
      password: 'aGoodPassword1',
      phoneno: '082 000 0000',
      account_type: 'resident',
      unit_no: 'A-101',
    });
  });

  it('submits estate details without a client-selected role or existing estate ID', () => {
    const payload = estateOnboardingPayload({ ...BASE, accountType: 'estate_admin' });

    expect(payload).toEqual({
      full_name: 'Thandi Nkosi',
      email: 'thandi@example.co.za',
      password: 'aGoodPassword1',
      phoneno: '082 000 0000',
      estate: {
        name: 'Ridge Close Estate',
        suburb: 'Centurion',
        city: 'Tshwane',
        province: 'Gauteng',
        description: 'A 24-unit complex.',
      },
    });
    expect(payload).not.toHaveProperty('account_type');
    expect(payload).not.toHaveProperty('role');
    expect(payload).not.toHaveProperty('estate_id');
  });
});

describe('Register', () => {
  it('offers resident, HOA, and provider paths with accessible descriptions', () => {
    renderRegister();

    expect(screen.getByRole('radio', { name: 'Resident' })).toHaveAccessibleDescription(
      /join with a code from your estate office/i,
    );
    expect(screen.getByRole('radio', { name: /HOA \/ estate manager/i })).toBeVisible();
    expect(screen.getByRole('radio', { name: /service provider/i })).toHaveAccessibleDescription(
      /apply to an estate.*HOA reviews/i,
    );
  });

  it('creates a resident through the existing public registration path', async () => {
    const user = userEvent.setup();
    renderRegister();
    await user.type(screen.getByLabelText('Full name'), 'Thandi Nkosi');
    await user.type(screen.getByLabelText('Email address'), 'thandi@example.co.za');
    await user.type(screen.getByLabelText('Password'), 'aGoodPassword1');
    await user.click(screen.getByRole('button', { name: 'Create resident account' }));

    await waitFor(() => expect(auth.register).toHaveBeenCalledOnce());
    expect(auth.register).toHaveBeenCalledWith(expect.objectContaining({ account_type: 'resident' }));
    expect(auth.registerEstate).not.toHaveBeenCalled();
  });

  it('creates a new HOA estate through its dedicated onboarding path', async () => {
    const user = userEvent.setup();
    renderRegister();
    await user.click(screen.getByRole('radio', { name: /HOA \/ estate manager/i }));
    await user.type(screen.getByLabelText('Full name'), 'Amina Manager');
    await user.type(screen.getByLabelText('Email address'), 'amina@example.co.za');
    await user.type(screen.getByLabelText('Password'), 'aGoodPassword1');
    await user.type(screen.getByLabelText('Estate name'), 'Ridge Close Estate');
    await user.type(screen.getByLabelText('Suburb'), 'Centurion');
    await user.type(screen.getByLabelText('City'), 'Tshwane');
    await user.selectOptions(screen.getByLabelText('Province'), 'Gauteng');
    await user.click(screen.getByRole('button', { name: 'Create estate workspace' }));

    await waitFor(() => expect(auth.registerEstate).toHaveBeenCalledOnce());
    expect(auth.register).not.toHaveBeenCalled();
    expect(auth.registerEstate).toHaveBeenCalledWith(
      expect.objectContaining({
        email: 'amina@example.co.za',
        estate: expect.objectContaining({ name: 'Ridge Close Estate' }),
      }),
    );
  });

  it('routes providers to an estate application instead of creating an account', async () => {
    const user = userEvent.setup();
    renderRegister();
    await user.click(screen.getByRole('radio', { name: /service provider/i }));

    expect(screen.getByText(/the HOA reviews your application/i)).toBeVisible();
    expect(screen.getByRole('link', { name: /apply to an estate/i })).toHaveAttribute('href', '/provider/apply');
    expect(screen.queryByRole('button', { name: /create .*account/i })).toBeNull();
    expect(auth.register).not.toHaveBeenCalled();
    expect(auth.registerEstate).not.toHaveBeenCalled();
  });

  it('lets a signed-in user sign out and switch accounts without leaving registration', async () => {
    const user = userEvent.setup();
    auth.user = { full_name: 'Thandi Nkosi', email: 'thandi@example.co.za' };
    renderRegister();

    await user.click(screen.getByRole('button', { name: /sign out and switch accounts/i }));

    expect(auth.logout).toHaveBeenCalledOnce();
    expect(screen.getByRole('radio', { name: 'Resident' })).toBeVisible();
  });
});
