/**
 * The drawer must show the state the server is actually in after a write.
 *
 * This exists because the live acceptance run found the opposite: the HOA moved a
 * complaint under review, the register behind the drawer updated, and the drawer
 * itself kept showing "Move this complaint under review before assigning a
 * provider" — the fetch it made after the write was served from the browser cache.
 * A control that reports a state the server has left is worse than no control.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ComplaintDrawer } from './ComplaintDrawer';
const mocks = vi.hoisted(() => ({ get: vi.fn(), patch: vi.fn(), post: vi.fn() }));
vi.mock('../lib/api', () => ({
    ApiError: class ApiError extends Error {
        status = 0;
    },
    api: { get: mocks.get, post: mocks.post, patch: mocks.patch, remove: vi.fn() },
}));
vi.mock('../lib/estateAdmin', () => ({
    listEstateProviders: vi.fn(async () => ({ items: [], total: 0, page: 1, size: 100, pages: 1 })),
    getComplaintWorkOrder: vi.fn(async () => {
        throw new Error('not used in this test');
    }),
    rateWorkOrder: vi.fn(),
}));
vi.mock('../lib/ai', () => ({
    readTriageSuggestion: vi.fn(async () => {
        throw new Error('no suggestion');
    }),
    requestTriageSuggestion: vi.fn(),
    decideTriageSuggestion: vi.fn(),
    isAiUnavailable: () => false,
}));
vi.mock('../context/AuthContext', () => ({
    useAuth: () => ({ user: { id: 1, role: 'hoa_admin' }, checking: false }),
}));
vi.mock('../context/EstateContext', () => ({
    useEstateScope: () => ({
        estateId: 4,
        estate: { estate_id: 4, estate_name: 'Ridge Close' },
        loading: false,
        error: null,
        reload: vi.fn(),
    }),
}));
function complaint(status) {
    return {
        id: 39,
        user_id: 7,
        estate_id: 4,
        unit_id: 1,
        category: 'water',
        description: 'Burst pipe under the kitchen sink.',
        priority: 'urgent',
        is_anonymous: false,
        status,
        assigned_to: null,
        reviewed_at: status === 'submitted' ? null : '2026-10-12T06:00:00Z',
        assigned_at: null,
        started_at: null,
        resolved_at: null,
        created_at: '2026-10-12T05:00:00Z',
        updated_at: null,
    };
}
beforeEach(() => {
    mocks.get.mockReset();
    mocks.patch.mockReset();
    mocks.post.mockReset();
    mocks.get.mockImplementation(async (path) => {
        if (path === '/api/v1/complaints/39')
            return complaint('submitted');
        if (path === '/api/v1/complaints/39/events')
            return [];
        return { items: [], total: 0, page: 1, size: 10, pages: 0 };
    });
    mocks.patch.mockResolvedValue(complaint('reviewed'));
});
describe('ComplaintDrawer — after a status change', () => {
    it('re-reads the complaint and offers the assignment step', async () => {
        const user = userEvent.setup();
        render(<ComplaintDrawer complaintId={39} onClose={() => { }} onChanged={() => { }}/>);
        await expect(screen.findByText(/Move this complaint under review before assigning a provider/)).resolves.toBeVisible();
        // The server is now in `reviewed`; the next read must say so.
        mocks.get.mockImplementation(async (path) => {
            if (path === '/api/v1/complaints/39')
                return complaint('reviewed');
            if (path === '/api/v1/complaints/39/events')
                return [];
            return { items: [], total: 0, page: 1, size: 10, pages: 0 };
        });
        await user.click(screen.getByRole('button', { name: 'Mark under review' }));
        expect(mocks.patch).toHaveBeenCalledWith('/api/v1/complaints/39/status', { status: 'reviewed', note: null }, { estate_id: 4 });
        expect(await screen.findByLabelText(/Verified provider/)).toBeVisible();
        expect(screen.queryByText(/Move this complaint under review/)).toBeNull();
    });
});
