import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Login } from './Login';

const auth = vi.hoisted(() => ({
  user: null,
  logout: vi.fn(),
  login: vi.fn(),
}));

vi.mock('../context/AuthContext', () => ({
  useAuth: () => auth,
}));

beforeEach(() => {
  auth.user = null;
  vi.clearAllMocks();
});

describe('Login', () => {
  it('keeps the sign-in route open for an existing session and offers account switching', async () => {
    const user = userEvent.setup();
    auth.user = { full_name: 'Thandi Nkosi', email: 'thandi@example.co.za' };
    render(
      <MemoryRouter initialEntries={['/login']}>
        <Login />
      </MemoryRouter>,
    );

    expect(screen.getByRole('status')).toHaveTextContent(/signed in as thandi@example\.co\.za/i);
    expect(screen.getByRole('link', { name: 'Continue to workspace' })).toHaveAttribute(
      'href',
      '/welcome',
    );

    await user.click(screen.getByRole('button', { name: /sign out and switch accounts/i }));

    expect(auth.logout).toHaveBeenCalledOnce();
    expect(screen.getByRole('textbox', { name: 'Email address' })).toBeVisible();
    expect(auth.login).not.toHaveBeenCalled();
  });
});
