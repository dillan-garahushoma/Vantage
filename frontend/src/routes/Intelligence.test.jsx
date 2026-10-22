/**
 * VALORA Intelligence — the whole path, from the briefing to the API.
 *
 * This is the wiring test for the batch's star feature:
 *
 *  * the weekly briefing and its three priority recommendations render with their
 *    evidence and their rand value;
 *  * “Review” opens the drawer with the source signals behind a finding;
 *  * “Create work order” opens a dialog that submits VALORA's *real* contract —
 *    `POST /api/v1/work-orders` with `complaint_id` and `provider_id`, because a
 *    work order is the assignment of a provider to a complaint and not a
 *    free-standing job record;
 *  * “Ask VALORA” answers a suggested prompt with a structured response.
 *
 * Intelligence responses are explicitly fictional API fixtures for UI wiring tests.
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { priorityRecommendations, weeklyBriefing } from './intelligenceFixtures';
const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
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
        get isForbidden() {
            return this.status === 403;
        }
    },
    api: { get: mocks.get, post: mocks.post, patch: vi.fn(), remove: vi.fn() },
    session: { token: () => 'test-token', user: () => null },
}));
vi.mock('../context/AuthContext', () => ({
    useAuth: () => ({
        user: { id: 1, full_name: 'Thandi Nkosi', role: 'hoa_admin' },
        checking: false,
    }),
}));
vi.mock('../context/EstateContext', () => ({
    useEstateScope: () => ({
        estateId: 1,
        estate: { is_estate_admin: true, estate_id: 1, estate_name: 'Greenhaven Estate', property_ids: [4, 9] },
        loading: false,
        error: null,
        reload: vi.fn(),
        livingScore: {
            value: 82,
            trend: 4,
            label: 'Healthy, with watch areas',
            status: 'scored',
            history: [78, 82],
            calculatedAt: '2026-10-04T06:00:01Z',
            loading: false,
        },
    }),
    useEstate: () => ({
        estates: [],
        active: { estate_id: 1, estate_name: 'Greenhaven Estate' },
        loading: false,
        error: null,
        awaitingProvisioning: false,
        selectEstate: vi.fn(),
        reload: vi.fn(),
        livingScore: {
            value: 82,
            trend: 4,
            label: 'Healthy, with watch areas',
            status: 'scored',
            history: [78, 82],
            calculatedAt: '2026-10-04T06:00:01Z',
            loading: false,
        },
    }),
}));
import { Toaster } from '../components/ui/toast';
import { Intelligence } from './Intelligence';
const openComplaint = {
    id: 12,
    user_id: 3,
    estate_id: 1,
    unit_id: 4,
    category: 'water',
    description: 'Irrigation pressure is low across Block C and the cycle runs long.',
    priority: 'high',
    is_anonymous: false,
    status: 'submitted',
    assigned_to: null,
    reviewed_at: null,
    assigned_at: null,
    started_at: null,
    resolved_at: null,
    created_at: '2026-10-14T06:00:00Z',
    updated_at: null,
};
function pageOf(items, total = items.length) {
    return { items, total, page: 1, size: 20, pages: 1 };
}
beforeEach(() => {
    mocks.get.mockReset();
    mocks.post.mockReset();
    mocks.post.mockImplementation(async (path) => path.endsWith('/ask')
        ? { summary: 'The stored score has no comparable prior snapshot.', evidence: ['Stored snapshot #1'], recommendation: 'Review the source records.', related: ['Estate health'], source: 'estate-domain' }
        : { id: 21, complaint_id: 12, provider_id: 5, status: 'assigned' });
    mocks.get.mockImplementation(async (path) => {
        if (path === '/api/v1/analytics/intelligence')
            return { briefing: weeklyBriefing, recommendations: priorityRecommendations,
                operational_signals: { open_complaints: 105, work_orders_in_flight: 2, unresolved_incidents: 1 } };
        if (path === '/api/v1/analytics/intelligence/history')
            return { items: [{ estate_id: 1, estate_name: 'Greenhaven Estate', briefing_id: 88,
                        as_of: '2026-10-15T08:00:00Z', briefing: weeklyBriefing,
                        recommendations: [], operational_signals: { open_complaints: 3, work_orders_in_flight: 1, unresolved_incidents: 0 },
                        source: 'stored_records' }], total: 1, page: 1, size: 10, pages: 1 };
        if (path === '/api/v1/analytics/intelligence/history/88')
            return { estate_id: 1, estate_name: 'Greenhaven Estate', briefing_id: 88,
                as_of: '2026-10-15T08:00:00Z', briefing: { ...weeklyBriefing, headline: 'Saved maintenance briefing' },
                recommendations: [], operational_signals: { open_complaints: 3, work_orders_in_flight: 1, unresolved_incidents: 0 },
                source: 'stored_records' };
        if (path === '/api/v1/complaints')
            return pageOf([openComplaint]);
        if (path === '/api/v1/providers') {
            return pageOf([
                {
                    id: 5,
                    full_name: 'AquaFix Plumbing',
                    trade: 'plumbing',
                    phone: '000 000 0000',
                    email: 'ops@aquafix.example',
                    avg_rating: '4.60',
                    total_reviews: 12,
                    verified: true,
                    emergency_available: true,
                },
            ]);
        }
        return pageOf([]);
    });
});
function renderPage() {
    return render(<MemoryRouter initialEntries={['/intelligence']}>
      <Intelligence />
      {/* The shell mounts this in `main.jsx`; a confirmed success is announced
            there, so the submission test needs it here too. */}
      <Toaster />
    </MemoryRouter>);
}
describe('VALORA Intelligence', () => {
    it('uses server counts beyond the first page and can save a current briefing', async () => {
        const user = userEvent.setup();
        renderPage();
        expect(await screen.findByText('105')).toBeVisible();
        await user.click(screen.getByRole('button', { name: 'Save current briefing' }));
        await waitFor(() => expect(mocks.post).toHaveBeenCalledWith(
            '/api/v1/analytics/intelligence/briefing/generate', {}, { estate_id: 1 }));
    });

    it('loads a saved briefing only from the estate-scoped history endpoint', async () => {
        const user = userEvent.setup();
        renderPage();
        await user.click(await screen.findByRole('button', { name: 'View saved briefing 88' }));
        expect(await screen.findByText('Saved maintenance briefing')).toBeVisible();
        expect(mocks.get).toHaveBeenCalledWith('/api/v1/analytics/intelligence/history/88', { estate_id: 1 });
    });

    it('renders an API denial without showing fictional recommendations', async () => {
        mocks.get.mockRejectedValue(new Error('Estate access denied'));
        renderPage();
        expect(await screen.findByText('Intelligence unavailable')).toBeVisible();
        expect(screen.getByText('Estate access denied')).toBeVisible();
        expect(screen.queryByText(priorityRecommendations[0].title)).not.toBeInTheDocument();
        expect(screen.queryByText('R42,000')).not.toBeInTheDocument();
    });

    it('shows ask errors without replacing them with a made-up answer', async () => {
        mocks.post.mockRejectedValue(new Error('Estate access denied'));
        const user = userEvent.setup();
        renderPage();
        await user.click(await screen.findByRole('button', { name: 'Why did our estate health score change?' }));
        expect(await screen.findByRole('alert')).toHaveTextContent('Estate access denied');
        expect(screen.queryByText('Summary')).not.toBeInTheDocument();
    });

    it('renders the weekly briefing and every priority recommendation with its impact', async () => {
        renderPage();
        expect(await screen.findByText('Three issues deserve attention this week.')).toBeVisible();
        expect(screen.getByText(/prevent an estimated R86,000 in reactive maintenance/)).toBeVisible();
        for (const recommendation of priorityRecommendations) {
            expect(screen.getByText(recommendation.title)).toBeVisible();
            expect(screen.getByText(recommendation.kind)).toBeVisible();
        }
        expect(screen.getByText('R42,000')).toBeVisible();
        expect(screen.getByText('R28,000')).toBeVisible();
        expect(screen.getByText('R16,000')).toBeVisible();
        expect(screen.getAllByText('Every finding traceable to source').length).toBeGreaterThan(0);
    });
    it('opens the review drawer with the source signals behind a finding', async () => {
        const user = userEvent.setup();
        renderPage();
        const reviewButtons = await screen.findAllByRole('button', { name: /review/i });
        await user.click(reviewButtons[0]);
        expect(await screen.findByText('Source signals')).toBeVisible();
        // The source badge appears on the card and again in the review.
        expect(screen.getAllByText('SCADA relay log · Clubhouse pump plant').length).toBeGreaterThan(0);
        expect(screen.getByText('Suggested action')).toBeVisible();
        expect(screen.getByText(/This is a recommendation, not a recorded outcome/)).toBeVisible();
    });
    it('raises the work order through the API’s real contract', async () => {
        const user = userEvent.setup();
        renderPage();
        const actionButtons = await screen.findAllByRole('button', { name: /create work order/i });
        await user.click(actionButtons[0]);
        // The dialog loads the estate's open complaints and its provider directory,
        // and the finding's own cost estimate is already in the form.
        const provider = await screen.findByLabelText('Provider');
        await user.selectOptions(provider, '5');
        expect(screen.getByLabelText('Quoted cost (ZAR)')).toHaveValue('9800');
        await user.click(screen.getByRole('button', { name: /^Create work order$/ }));
        await waitFor(() => expect(mocks.post).toHaveBeenCalledTimes(1));
        const [path, body, params] = mocks.post.mock.calls[0];
        expect(path).toBe('/api/v1/work-orders');
        expect(params).toEqual({ estate_id: 1 });
        expect(body).toMatchObject({ complaint_id: 12, provider_id: 5, job_cost: 9800 });
        expect(await screen.findByText(/Work order raised/)).toBeVisible();
    });
    it('answers a suggested question with a structured response', async () => {
        const user = userEvent.setup();
        renderPage();
        await user.click(await screen.findByRole('button', {
            name: 'Why did our estate health score change?',
        }));
        expect(await screen.findByText('Summary', {}, { timeout: 4000 })).toBeVisible();
        // The answer card repeats the card labels (“Evidence”, “Recommendation”), so
        // the structured sections are asserted by their distinct copy instead.
        expect(screen.getAllByText('Evidence').length).toBeGreaterThan(1);
        expect(screen.getByText('Recommendation')).toBeVisible();
        expect(screen.getByText('Related records')).toBeVisible();
        // Answered from the estate's stored records, and the footer says so.
        expect(screen.getByText(/answered from the estate’s stored records/i)).toBeVisible();
    });
});
