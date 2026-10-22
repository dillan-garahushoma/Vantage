import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PasswordRecovery } from './PasswordRecovery';

const mocks = vi.hoisted(() => ({ request: vi.fn(), confirm: vi.fn() }));
vi.mock('../lib/accountSupport', () => ({
    requestPasswordRecovery: mocks.request,
    confirmPasswordRecovery: mocks.confirm,
}));

beforeEach(() => {
    mocks.request.mockReset();
    mocks.confirm.mockReset();
});

describe('PasswordRecovery', () => {
    it('accepts an email and gives the backend’s non-enumerating response', async () => {
        mocks.request.mockResolvedValue({ message: 'If the account is eligible and email is enabled, recovery instructions will be sent.' });
        const user = userEvent.setup();
        render(<MemoryRouter><PasswordRecovery /></MemoryRouter>);
        await user.type(screen.getByLabelText('Email address'), 'resident@example.com');
        await user.click(screen.getByRole('button', { name: 'Send recovery instructions' }));
        expect(mocks.request).toHaveBeenCalledWith('resident@example.com');
        expect(await screen.findByText(/If the account is eligible/)).toBeVisible();
    });

    it('only sends the reset token and new password to the confirmation endpoint', async () => {
        mocks.confirm.mockResolvedValue({ message: 'Password changed. Sign in again.' });
        const user = userEvent.setup();
        render(<MemoryRouter initialEntries={['/password-recovery?token=recovery-token-123456789012345678901']}><PasswordRecovery /></MemoryRouter>);
        await user.type(screen.getByLabelText('New password'), 'NewSecurePass1');
        await user.type(screen.getByLabelText('Confirm new password'), 'NewSecurePass1');
        await user.click(screen.getByRole('button', { name: 'Set new password' }));
        expect(mocks.confirm).toHaveBeenCalledWith('recovery-token-123456789012345678901', 'NewSecurePass1');
        expect(await screen.findByText('Password changed. Sign in again.')).toBeVisible();
    });
});
