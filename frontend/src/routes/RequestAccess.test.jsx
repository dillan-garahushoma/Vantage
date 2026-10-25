/**
 * Asking to join an estate, for approval.
 *
 * The screen makes three promises the test pins: nothing is granted until an
 * administrator decides, the resident can request estate membership without
 * disclosing a unit number, and a rejected submission is the server's own
 * message rather than a guess.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../lib/api';
import { RequestAccess } from './RequestAccess';
const mocks = vi.hoisted(() => ({
    listPublic: vi.fn(),
    submit: vi.fn(),
    mine: vi.fn(),
    reloadEstates: vi.fn(),
}));
vi.mock('../lib/publicDirectory', () => ({ listPublicEstates: mocks.listPublic }));
// The pure helpers (RESIDENCY_STATUS, asResidencyStatus) stay real; only the two
// network calls are doubled.
vi.mock('../lib/residency', async (importOriginal) => {
    const actual = await importOriginal();
    return { ...actual, submitResidencyRequest: mocks.submit, listMyResidencyRequests: mocks.mine };
});
vi.mock('../context/AuthContext', () => ({
    useAuth: () => ({ user: { id: 1, full_name: 'Thandi Nkosi', role: 'resident' } }),
}));
vi.mock('../context/EstateContext', () => ({
    useEstate: () => ({ reload: mocks.reloadEstates }),
    useEstateScope: () => ({ estateId: null, estate: null }),
}));
const ESTATES = {
    items: [
        {
            estate_id: 4,
            name: 'Zambezi Country Estate',
            suburb: 'Montana',
            city: 'Pretoria',
            province: 'Gauteng',
            unit_count: 24,
            description: null,
            cover_photo_public_id: null,
        },
    ],
    total: 1,
    page: 1,
    size: 8,
    pages: 1,
};
function renderScreen() {
    return render(<MemoryRouter initialEntries={['/request-access']}>
      <RequestAccess />
    </MemoryRouter>);
}
beforeEach(() => {
    mocks.listPublic.mockReset();
    mocks.submit.mockReset();
    mocks.mine.mockReset();
    mocks.reloadEstates.mockReset();
    mocks.listPublic.mockResolvedValue(ESTATES);
    mocks.mine.mockResolvedValue([]);
    window.sessionStorage.clear();
});
describe('RequestAccess', () => {
    it('promises that no access is granted until an administrator approves', () => {
        renderScreen();
        expect(screen.getByRole('heading', { level: 1, name: /ask to join your estate/i })).toBeVisible();
        expect(screen.getByText(/you will not have access until they approve it/i)).toBeVisible();
        // A join code is offered as the alternative, not hidden.
        expect(screen.getByRole('link', { name: /redeem it instead/i })).toBeVisible();
    });
    it('requires a complex before spending a request, but never requires a unit', async () => {
        const user = userEvent.setup();
        renderScreen();
        await user.click(screen.getByRole('button', { name: /send request for approval/i }));
        expect(await screen.findByText(/choose your complex first/i)).toBeVisible();
        expect(mocks.submit).not.toHaveBeenCalled();
        expect(screen.queryByRole('textbox', { name: /unit number/i })).toBeNull();
    });
    it('uses a complex selected from the public directory as form context only', async () => {
        window.sessionStorage.setItem('valora.public-estate-selection', JSON.stringify({
            estate_id: 4,
            name: 'Zambezi Country Estate',
            location: 'Montana, Pretoria, Gauteng',
        }));
        const user = userEvent.setup();
        renderScreen();
        expect(await screen.findByText('Zambezi Country Estate')).toBeVisible();
        await user.click(screen.getByRole('button', { name: /send request for approval/i }));
        expect(mocks.submit).toHaveBeenCalledWith({ estate_id: 4, note: null });
    });
    it('submits the chosen complex and note without asking for a unit', async () => {
        mocks.submit.mockResolvedValue({
            request_id: 31,
            estate_id: 4,
            estate_name: 'Zambezi Country Estate',
            unit_no: null,
            status: 'pending',
            applicant_name: 'Thandi Nkosi',
            applicant_email: 'thandi@example.co.za',
            created_at: '2026-10-13T09:30:00Z',
        });
        const user = userEvent.setup();
        renderScreen();
        await user.click(await screen.findByRole('button', { name: /zambezi country estate/i }));
        await user.type(screen.getByLabelText(/note to the estate office/i), 'Lease starts 1 Nov');
        await user.click(screen.getByRole('button', { name: /send request for approval/i }));
        expect(mocks.submit).toHaveBeenCalledWith({
            estate_id: 4,
            note: 'Lease starts 1 Nov',
        });
        expect(await screen.findByText(/request sent to zambezi country estate/i)).toBeVisible();
        expect(mocks.mine).toHaveBeenCalledTimes(2); // initial load + reload after submit
    });
    it('shows a duplicate request as the server’s own refusal', async () => {
        mocks.submit.mockRejectedValue(new ApiError(409, 'You already have a registration awaiting review for this estate.', 'CONFLICT', 'req-409'));
        const user = userEvent.setup();
        renderScreen();
        await user.click(await screen.findByRole('button', { name: /zambezi country estate/i }));
        await user.click(screen.getByRole('button', { name: /send request for approval/i }));
        expect(await screen.findByText('You cannot request this one')).toBeVisible();
        expect(screen.getByText(/already have a registration awaiting review/i)).toBeVisible();
        expect(screen.getByText(/req-409/)).toBeVisible();
    });
    it('lists the person’s own requests with a plain-language status', async () => {
        mocks.mine.mockResolvedValue([
            {
                request_id: 31,
                estate_id: 4,
                estate_name: 'Zambezi Country Estate',
                unit_no: null,
                status: 'approved',
                applicant_name: 'Thandi Nkosi',
                applicant_email: 'thandi@example.co.za',
                created_at: '2026-10-13T09:30:00Z',
                decided_at: '2026-10-13T10:00:00Z',
            },
        ]);
        renderScreen();
        expect(await screen.findByText('Approved')).toBeVisible();
        expect(screen.getByText(/you are a resident of this estate/i)).toBeVisible();
        expect(screen.getByRole('link', { name: /enter estate/i })).toHaveAttribute('href', '/app');
    });
});
