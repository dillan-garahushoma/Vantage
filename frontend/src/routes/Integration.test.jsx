import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Contact } from './Contact';
const mocks = vi.hoisted(() => ({ contact: vi.fn() }));
vi.mock('../lib/api', () => ({
    api: { contact: mocks.contact },
    ApiError: class ApiError extends Error {
        status = 0;
    },
}));
vi.mock('../context/AuthContext', () => ({
    useAuth: () => ({ user: { role: 'resident' } }),
}));
vi.mock('../context/EstateContext', () => ({
    useEstate: () => ({ loading: false, awaitingProvisioning: false, error: null }),
    useEstateScope: () => ({ estate: { estate_name: 'Current estate' }, estateId: 1 }),
}));
beforeEach(() => mocks.contact.mockReset());
describe('combined Vantage workspace', () => {
    it('sends the legacy contact journey through the current API and waits for success', async () => {
        mocks.contact.mockResolvedValue({ id: 12 });
        render(<MemoryRouter><Contact /></MemoryRouter>);
        fireEvent.change(screen.getByLabelText('Your name'), { target: { value: '  Resident Name  ' } });
        fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'resident@example.com' } });
        fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'Please contact me about joining the estate.' } });
        fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
        await waitFor(() => expect(mocks.contact).toHaveBeenCalledWith({
            name: 'Resident Name', email: 'resident@example.com', phone: null, subject: null,
            message: 'Please contact me about joining the estate.',
        }));
        expect(await screen.findByRole('status')).toHaveTextContent('Message received');
    });
    it('refuses invalid contact data without calling the backend', () => {
        render(<MemoryRouter><Contact /></MemoryRouter>);
        fireEvent.change(screen.getByLabelText('Your name'), { target: { value: 'R' } });
        fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'resident@example.com' } });
        fireEvent.submit(screen.getByRole('button', { name: 'Send message' }).closest('form'));
        expect(screen.getByRole('alert')).toHaveTextContent('Enter your name');
        expect(mocks.contact).not.toHaveBeenCalled();
    });
});
