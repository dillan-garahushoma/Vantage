import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Properties } from './Properties';

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }));
vi.mock('../lib/api', () => ({
    api,
    ApiError: class ApiError extends Error { constructor(status, message) { super(message); this.status = status; } },
}));
vi.mock('../context/AuthContext', () => ({ useAuth: () => ({ user: { id: 1, role: 'hoa_admin' } }) }));
vi.mock('../context/EstateContext', () => ({
    useEstateScope: () => ({ estateId: 1, estate: { property_ids: [7], estate_name: 'Ridge Close' } }),
    useEstate: () => ({ estates: [], active: null, loading: false, error: null, awaitingProvisioning: false, selectEstate: vi.fn(), reload: vi.fn() }),
}));

const unit = { id: 7, estate_id: 1, unit_no: 'A-101', complex_name: 'Ridge Close', street_address: '1 Ridge Close', suburb: 'Centurion', size_m2: '88.00', bedrooms: 2, bathrooms: 1 };
const page = (items) => ({ items, total: items.length, page: 1, size: 100, pages: 1 });

beforeEach(() => {
    api.get.mockReset(); api.post.mockReset(); api.patch.mockReset();
    api.get.mockResolvedValue(page([unit]));
});

describe('Properties — management edits', () => {
    it('sends an HOA unit edit to the estate-scoped API and reloads the record', async () => {
        api.patch.mockResolvedValue({ ...unit, street_address: '11 Ridge Close' });
        const user = userEvent.setup();
        render(<MemoryRouter><Properties /></MemoryRouter>);
        await user.click(await screen.findByText('A-101'));
        await user.click(screen.getByRole('button', { name: 'Edit unit' }));
        const address = screen.getByLabelText('Street address');
        await user.clear(address);
        await user.type(address, '11 Ridge Close');
        await user.click(screen.getByRole('button', { name: 'Save unit changes' }));
        await waitFor(() => expect(api.patch).toHaveBeenCalledWith('/api/v1/properties/7', {
            street_address: '11 Ridge Close', size_m2: '88.00', bedrooms: 2, bathrooms: 1,
        }, { estate_id: 1 }));
    });
});
