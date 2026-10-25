/**
 * VALORA Intelligence — the whole path, from the briefing to the API.
 *
 * This is the wiring test for the batch's star feature:
 *
 *  * the weekly briefing and its three priority recommendations render with their
 *    evidence and their rand value;
 *  * "Review" opens the drawer with the source signals behind a finding;
 *  * "Create work order" opens a dialog that submits VALORA's *real* contract —
 *    `POST /api/v1/work-orders` with `complaint_id` and `provider_id`, because a
 *    work order is the assignment of a provider to a complaint and not a
 *    free-standing job record;
 *  * "Ask VALORA" opens the spotlight, streams a response, and shows errors.
 *
 * Intelligence responses are explicitly fictional API fixtures for UI wiring tests.
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ValoraChatProvider } from '../context/ValoraChatContext';
import { priorityRecommendations, weeklyBriefing } from './intelligenceFixtures';

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), streamAskValora: vi.fn() }));

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

/**
 * Mock the intelligence library so we can control streamAskValora
 * without touching the network or SSE plumbing.  The mock preserves all
 * named exports the route and components rely on (rolePrompts,
 * parseRecommendations …) by re-exporting the real module and only
 * swapping out streamAskValora.
 */
vi.mock('../lib/intelligence', async (importOriginal) => {
    const real = await importOriginal();
    return { ...real, streamAskValora: mocks.streamAskValora };
});

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
import { AskValoraSpotlight } from '../components/valora/AskValoraSpotlight';
import { Intelligence } from './Intelligence';
import { WorkOrders } from './WorkOrders';
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
    mocks.streamAskValora.mockReset();

    // Default: streamAskValora fires onToken once then onDone.
    mocks.streamAskValora.mockImplementation(async (_q, _ctx, { onMeta, onToken, onDone }) => {
        onMeta?.({
            evidence: ['Complaint #12 · Submitted'],
            related: ['What status is recorded for this issue?'],
            mode: 'ai_assisted',
        });
        onToken('VALORA has analysed the estate operational signals for this query.');
        onDone();
    });

    mocks.post.mockImplementation(async (path) => path.endsWith('/ask')
        ? { summary: 'The stored score has no comparable prior snapshot.', evidence: ['Stored snapshot #1'], recommendation: 'Review the source records.', related: ['Estate health'], source: 'estate-domain' }
        : { id: 21, complaint_id: 12, provider_id: 5, status: 'assigned' });
    mocks.get.mockImplementation(async (path) => {
        if (path === '/api/v1/analytics/intelligence')
            return { briefing: weeklyBriefing, recommendations: priorityRecommendations,
                role: 'hoa_admin',
                operational_signals: { open_complaints: 105, work_orders_in_flight: 2, unresolved_incidents: 1 } };
        if (path === '/api/v1/analytics/intelligence/history')
            return { items: [{ estate_id: 1, estate_name: 'Greenhaven Estate', briefing_id: 88,
                        as_of: '2026-10-15T08:00:00Z', briefing: weeklyBriefing,
                        recommendations: [], operational_signals: { open_complaints: 3, work_orders_in_flight: 1, unresolved_incidents: 0 },
                        source: 'stored_records' }], total: 1, page: 1, size: 10, pages: 1 };
        if (path === '/api/v1/analytics/intelligence/history/88')
            return { estate_id: 1, estate_name: 'Greenhaven Estate', briefing_id: 88,
                as_of: '2026-10-15T08:00:00Z', briefing: { ...weeklyBriefing, headline: 'Saved maintenance briefing' },
                role: 'hoa_admin',
                recommendations: [], operational_signals: { open_complaints: 3, work_orders_in_flight: 1, unresolved_incidents: 0 },
                source: 'stored_records' };
        if (path === '/api/v1/complaints')
            return pageOf([openComplaint]);
        if (path === '/api/v1/work-orders/52')
            return {
                id: 52,
                complaint_id: 12,
                provider_id: 5,
                estate_id: 1,
                status: 'overdue',
                assigned_at: '2026-10-10T08:00:00Z',
                estimated_completion_date: '2026-10-20',
                job_cost: '9800.00',
                completion_notes: null,
                actual_completion_date: null,
                resident_rating: null,
            };
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
    return render(
      <MemoryRouter initialEntries={['/intelligence']}>
        <ValoraChatProvider>
          <Intelligence />
          <AskValoraSpotlight />
          {/* The shell mounts this in `main.jsx`; a confirmed success is announced
                there, so the submission test needs it here too. */}
          <Toaster />
          <RouteProbe />
        </ValoraChatProvider>
      </MemoryRouter>
    );
}
function renderWorkOrdersWithFocusedRecord(workOrderId) {
    return render(
      <MemoryRouter initialEntries={[{
          pathname: '/app/work-orders',
          state: { focusWorkOrderId: workOrderId },
      }]}>
        <WorkOrders />
        <RouteProbe />
      </MemoryRouter>
    );
}
function RouteProbe() {
    const location = useLocation();
    return <output data-testid="route-probe">{`${location.pathname} ${JSON.stringify(location.state)}`}</output>;
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
        await waitFor(() => expect(mocks.get).toHaveBeenCalledWith(
            '/api/v1/analytics/intelligence/history', { estate_id: 1, size: 10 }));
        await user.click(await screen.findByRole('button', { name: 'View saved briefing 88' }));
        expect(await screen.findByText('Saved maintenance briefing')).toBeVisible();
        expect(mocks.get).toHaveBeenCalledWith('/api/v1/analytics/intelligence/history/88', { estate_id: 1 });
    });

    it('renders an API denial without showing fictional recommendations', async () => {
        mocks.get.mockRejectedValue(new Error('Estate access denied'));
        renderPage();
        expect(await screen.findByText('Briefing unavailable')).toBeVisible();
        expect(screen.getByText('Estate access denied')).toBeVisible();
        expect(screen.queryByText(priorityRecommendations[0].title)).not.toBeInTheDocument();
        expect(screen.queryByText('R42,000')).not.toBeInTheDocument();
    });

    it('shows ask errors without replacing them with a made-up answer', async () => {
        // Configure the stream mock to fire onError instead of onToken.
        mocks.streamAskValora.mockImplementation(async (_q, _ctx, { onError }) => {
            onError(new Error('Estate access denied'));
        });
        const user = userEvent.setup();
        renderPage();
        // The selected estate is administered by an HOA member, so show the
        // estate-operations prompts.
        const suggestedPrompt = await screen.findByRole('button', {
            name: 'What is the operational risk summary for this week?',
        });
        expect(suggestedPrompt).toBeEnabled();
        await user.click(suggestedPrompt);
        await waitFor(() => expect(mocks.streamAskValora).toHaveBeenCalled());
        // Keep the error and retryable question visible in the inline conversation.
        expect(await screen.findByText('Estate access denied')).toBeVisible();
        // No streamed AI answer should appear in the thread.
        expect(screen.queryByText('VALORA has analysed')).not.toBeInTheDocument();
    });

    it('keeps Ask VALORA available when the briefing endpoint fails', async () => {
        mocks.get.mockRejectedValue(new Error('Briefing service unavailable'));
        renderPage();
        expect(await screen.findByText('Briefing service unavailable')).toBeVisible();
        expect(screen.getByText('Ask VALORA')).toBeVisible();
        expect(screen.getByRole('button', { name: /What is the operational risk summary/i })).toBeVisible();
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
    it('raises the work order through the API\u2019s real contract', async () => {
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
    it('answers a suggested prompt inline and submits contextual follow-ups', async () => {
        const user = userEvent.setup();
        renderPage();
        // The hoa_admin suggestion buttons appear in the right-rail AskValora panel.
        // Clicking one starts the real stream in the inline conversation.
        await user.click(await screen.findByRole('button', {
            name: 'What is the operational risk summary for this week?',
        }));
        // The user's own question appears as a message bubble.
        expect(await screen.findByText(
            'What is the operational risk summary for this week?',
            { selector: 'p' }
        )).toBeVisible();
        // The streamed AI answer appears in the assistant bubble.
        const aiBubbles = await screen.findAllByText('VALORA has analysed the estate operational signals for this query.');
        expect(aiBubbles.length).toBeGreaterThan(0);
        expect(await screen.findByText('Complaint #12 · Submitted')).toBeVisible();
        const followUp = screen.getByRole('button', { name: 'What status is recorded for this issue?' });
        await user.click(followUp);
        await waitFor(() => expect(mocks.streamAskValora).toHaveBeenCalledTimes(2));
        expect(mocks.streamAskValora.mock.calls[1][0]).toBe('What status is recorded for this issue?');
        // The stream retains the selected estate context for each turn.
        const [question, context] = mocks.streamAskValora.mock.calls[0];
        expect(question).toBe('What is the operational risk summary for this week?');
        expect(context).toMatchObject({ estateId: 1 });
    });

    it('opens an existing overdue work order instead of offering a duplicate assignment', async () => {
        const defaultGet = mocks.get.getMockImplementation();
        mocks.get.mockImplementation(async (...args) => {
            const response = await defaultGet(...args);
            if (args[0] === '/api/v1/analytics/intelligence') {
                return {
                    ...response,
                    recommendations: response.recommendations.map((item, index) =>
                        index === 0 ? { ...item, id: 'overdue_work_order-52' } : item
                    ),
                };
            }
            return response;
        });
        const user = userEvent.setup();
        renderPage();

        await user.click(await screen.findByRole('link', { name: 'Open work order' }));

        expect(screen.getByTestId('route-probe')).toHaveTextContent(
            '/app/work-orders {"focusWorkOrderId":52}'
        );
    });

    it('loads the selected work-order detail through the estate-scoped endpoint', async () => {
        renderWorkOrdersWithFocusedRecord(52);

        await waitFor(() => expect(mocks.get).toHaveBeenCalledWith(
            '/api/v1/work-orders/52', { estate_id: 1 }));
        expect(await screen.findByText('WO-0052')).toBeVisible();
        await waitFor(() => expect(screen.getByTestId('route-probe'))
            .toHaveTextContent('/app/work-orders null'));
    });
});
