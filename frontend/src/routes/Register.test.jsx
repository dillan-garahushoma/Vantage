/** Public registration only creates residents; trusted accounts are operator-provisioned. */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { registrationPayload, Register } from './Register';
const mocks = vi.hoisted(() => ({ register: vi.fn() }));
vi.mock('../context/AuthContext', () => ({
    useAuth: () => ({ user: null, register: mocks.register }),
}));
beforeEach(() => {
    mocks.register.mockReset();
});
function renderRegister() {
    return render(<MemoryRouter>
      <Register />
    </MemoryRouter>);
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
        const payload = registrationPayload({
            ...BASE,
            phoneno: '   ',
            unit_no: '',
            estateDescription: '  ',
        });
        expect(payload).not.toHaveProperty('phoneno');
        expect(payload).not.toHaveProperty('unit_no');
    });
    it('ignores a stale trusted-account choice and only sends resident registration data', () => {
        const payload = registrationPayload({ ...BASE, accountType: 'estate_admin' });
        expect(payload.account_type).toBe('resident');
        expect(payload).not.toHaveProperty('role');
        expect(payload).not.toHaveProperty('estate');
        expect(payload).not.toHaveProperty('provider');
    });
});
describe('Register — resident account', () => {
    it('has one resident account type and explains that trusted accounts are provisioned', async () => {
        renderRegister();
        const radio = screen.getByRole('radio', { name: 'Resident' });
        expect(radio).toBeChecked();
        expect(radio).toHaveAccessibleDescription(/join with a code from your estate office/i);
        expect(screen.queryByRole('radio', { name: /service provider/i })).toBeNull();
        expect(screen.getByText(/estate office provisions manager and provider accounts/i)).toBeVisible();
    });
});
