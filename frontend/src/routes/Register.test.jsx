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

const progress = () => screen.getByRole('progressbar', { name: 'Registration progress' });
const fillWidth = () => Number.parseFloat(progress().firstElementChild.style.width);
const continueButton = () => screen.getByRole('button', { name: 'Continue' });

async function fillDetails(user, { name = 'Thandi Nkosi', email = 'thandi@example.co.za' } = {}) {
  await user.type(screen.getByLabelText('Full name'), name);
  await user.type(screen.getByLabelText('Email address'), email);
  await user.type(screen.getByLabelText('Password'), 'aGoodPassword1');
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

  it('opens on step one of three and offers no submit before the details exist', () => {
    renderRegister();

    expect(progress()).toHaveAttribute('aria-valuenow', '1');
    // The bar fills by stage: one of three at the start, never empty.
    expect(fillWidth()).toBeCloseTo(100 / 3, 3);
    expect(screen.getByRole('heading', { name: 'How will you use VALORA?' })).toBeVisible();
    expect(screen.queryByLabelText('Full name')).toBeNull();
    expect(screen.queryByRole('button', { name: /create .*account/i })).toBeNull();
  });

  it('walks the three steps and keeps answers when going back', async () => {
    const user = userEvent.setup();
    renderRegister();

    await user.click(continueButton());
    expect(progress()).toHaveAttribute('aria-valuenow', '2');
    expect(fillWidth()).toBeCloseTo(200 / 3, 3);
    expect(screen.getByRole('heading', { name: 'Your details' })).toBeVisible();

    await user.type(screen.getByLabelText('Full name'), 'Thandi Nkosi');
    await user.click(screen.getByRole('button', { name: 'Back' }));
    expect(progress()).toHaveAttribute('aria-valuenow', '1');

    await user.click(continueButton());
    expect(screen.getByLabelText('Full name')).toHaveValue('Thandi Nkosi');
  });

  it('holds the details step until the answers are valid', async () => {
    const user = userEvent.setup();
    renderRegister();

    await user.click(continueButton());
    await user.click(continueButton());

    expect(progress()).toHaveAttribute('aria-valuenow', '2');
    expect(screen.getByRole('heading', { name: 'Your details' })).toBeVisible();
    expect(screen.getByText('Enter your full name.')).toBeVisible();
    expect(auth.register).not.toHaveBeenCalled();
  });

  it('asks for a review before creating the account', async () => {
    const user = userEvent.setup();
    renderRegister();

    await user.click(continueButton());
    await fillDetails(user);
    await user.click(continueButton());

    expect(progress()).toHaveAttribute('aria-valuenow', '3');
    expect(fillWidth()).toBeCloseTo(100, 3);
    expect(screen.getByRole('heading', { name: 'Review and create' })).toBeVisible();
    expect(screen.getByText('thandi@example.co.za')).toBeVisible();
    expect(auth.register).not.toHaveBeenCalled();
  });

  it('creates a resident through the existing public registration path', async () => {
    const user = userEvent.setup();
    renderRegister();
    await user.click(continueButton());
    await fillDetails(user);
    await user.click(continueButton());
    await user.click(screen.getByRole('button', { name: 'Create resident account' }));

    await waitFor(() => expect(auth.register).toHaveBeenCalledOnce());
    expect(auth.register).toHaveBeenCalledWith(expect.objectContaining({ account_type: 'resident' }));
    expect(auth.registerEstate).not.toHaveBeenCalled();
  });

  it('creates a new HOA estate through its dedicated onboarding path', async () => {
    const user = userEvent.setup();
    renderRegister();
    await user.click(screen.getByRole('radio', { name: /HOA \/ estate manager/i }));
    await user.click(continueButton());
    await user.type(screen.getByLabelText('Full name'), 'Amina Manager');
    await user.type(screen.getByLabelText('Email address'), 'amina@example.co.za');
    await user.type(screen.getByLabelText('Password'), 'aGoodPassword1');
    await user.click(continueButton());
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
    expect(screen.queryByRole('progressbar', { name: 'Registration progress' })).toBeNull();
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
