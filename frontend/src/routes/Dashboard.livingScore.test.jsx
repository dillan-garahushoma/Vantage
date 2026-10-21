/**
 * The dashboard asks the API for the estate's stored Living Score and shows it.
 *
 * This is the wiring test for the gap the P3 session recorded: the endpoint
 * existed and the panel rendered `score={null}` unconditionally. Here the request
 * is asserted (the right path, `estate_id` as a query parameter) and the stored
 * snapshot is asserted to reach the screen.
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), role: 'resident' }));
vi.mock('../lib/api', () => ({
    ApiError: class ApiError extends Error {
        status;
        code;
        requestId;
        constructor(status, message, code, requestId) {
            super(message);
            this.status = status;
            this.code = code;
            this.requestId = requestId;
        }
    },
    api: { get: mocks.get, post: mocks.post, patch: vi.fn(), remove: vi.fn() },
    session: { token: () => 'test-token', user: () => null },
}));
vi.mock('../lib/ai', () => ({
    readHealthBrief: vi.fn(async () => {
        throw new Error('no brief in this test');
    }),
    generateHealthBrief: vi.fn(),
    sendHealthBriefFeedback: vi.fn(),
}));
vi.mock('../context/AuthContext', () => ({
    useAuth: () => ({
        user: { id: 1, full_name: 'Thandi Nkosi', role: mocks.role },
        checking: false,
    }),
}));
vi.mock('../context/EstateContext', () => ({
    useEstateScope: () => ({
        estateId: 1,
        estate: {
            estate_id: 1,
            estate_name: 'Ridge Close',
            suburb: 'Centurion',
            city: 'Tshwane',
            province: 'Gauteng',
            is_estate_admin: false,
            is_estate_provider: false,
            membership_roles: ['resident'],
            property_ids: [3],
        },
        loading: false,
        error: null,
        reload: vi.fn(),
    }),
    useEstate: () => ({
        estates: [],
        active: { estate_id: 1, estate_name: 'Ridge Close' },
        loading: false,
        error: null,
        awaitingProvisioning: false,
        selectEstate: vi.fn(),
        reload: vi.fn(),
    }),
}));
import { Dashboard } from './Dashboard';
function emptyPage() {
    return { items: [], total: 0, page: 1, size: 20, pages: 1 };
}
function livingScore() {
    return {
        id: 9,
        estate_id: 1,
        engine_version: '1.0.0',
        as_of: '2026-10-04T06:00:00Z',
        window_start: '2026-07-06T06:00:00Z',
        calculated_at: '2026-10-04T06:00:01Z',
        status: 'scored',
        overall_score: '86.4',
        measured_weight: '1.00',
        is_demo: true,
        components: [
            {
                key: 'resolution',
                label: 'Resolution speed',
                weight: '0.30',
                status: 'measured',
                score: '90',
                inputs: {},
                benchmark: '',
                explanation: '',
            },
        ],
        drivers: [],
    };
}
function statsPayload() {
    return {
        total: 0,
        by_status: {},
        resolution_rate_pct: '0.00',
        avg_resolution_hours: null,
    };
}
beforeEach(() => {
    mocks.role = 'resident';
    mocks.get.mockReset();
    mocks.post.mockReset();
    mocks.post.mockResolvedValue(livingScore());
    mocks.get.mockImplementation(async (path) => {
        if (path === '/api/v1/analytics/living-score')
            return livingScore();
        if (path === '/api/v1/complaints/stats')
            return statsPayload();
        return emptyPage();
    });
});
describe('Dashboard — Living Score', () => {
    it('requests the estate’s stored score with estate_id and renders it', async () => {
        render(<MemoryRouter initialEntries={['/app']}>
        <Dashboard />
      </MemoryRouter>);
        expect(await screen.findByText('86,4')).toBeVisible();
        expect(screen.queryByText('Demo data')).toBeNull();
        expect(screen.getByText('Resolution speed')).toBeVisible();
        expect(mocks.get).toHaveBeenCalledWith('/api/v1/analytics/living-score', {
            estate_id: 1,
        });
    });
    it('shows the "not enough data yet" state instead of a number when the estate has never been scored', async () => {
        mocks.get.mockImplementation(async (path) => {
            if (path === '/api/v1/analytics/living-score') {
                const { ApiError } = await import('../lib/api');
                throw new ApiError(404, 'No Living Score has been calculated for this estate yet.');
            }
            return emptyPage();
        });
        render(<MemoryRouter initialEntries={['/app']}>
        <Dashboard />
      </MemoryRouter>);
        expect(await screen.findByText('Not enough data yet')).toBeVisible();
        expect(screen.queryByText('86,4')).toBeNull();
        // The "engine pending" strip is only shown while nothing is stored at all.
        expect(screen.getByText('What the Living Score needs')).toBeVisible();
    });
    it('lets an HOA administrator recalculate, and re-reads the stored score afterwards', async () => {
        mocks.role = 'hoa_admin';
        const user = userEvent.setup();
        render(<MemoryRouter initialEntries={['/app']}>
        <Dashboard />
      </MemoryRouter>);
        await user.click(await screen.findByRole('button', { name: /recalculate now/i }));
        expect(mocks.post).toHaveBeenCalledWith('/api/v1/analytics/living-score/recalculate', {}, { estate_id: 1 });
        // A fresh read, never a locally adjusted number.
        await waitFor(() => expect(mocks.get.mock.calls.filter(([path]) => path === '/api/v1/analytics/living-score')
            .length).toBe(2));
    });
    it('offers no recalculation to somebody the server would refuse', async () => {
        render(<MemoryRouter initialEntries={['/app']}>
        <Dashboard />
      </MemoryRouter>);
        await screen.findByText('86,4');
        expect(screen.queryByRole('button', { name: /recalculate/i })).toBeNull();
    });
    it('shows the server’s refusal verbatim when the recalculation is not allowed', async () => {
        mocks.role = 'hoa_admin';
        const { ApiError } = await import('../lib/api');
        mocks.post.mockRejectedValue(new ApiError(403, 'This account is not an administrator of this estate.', 'FORBIDDEN', 'req-403'));
        const user = userEvent.setup();
        render(<MemoryRouter initialEntries={['/app']}>
        <Dashboard />
      </MemoryRouter>);
        await user.click(await screen.findByRole('button', { name: /recalculate now/i }));
        expect(await screen.findByText(/The recalculation was refused/)).toBeVisible();
        expect(screen.getByText('This account is not an administrator of this estate.')).toBeVisible();
        expect(screen.getByText(/req-403/)).toBeVisible();
    });
});
