/**
 * Triage suggestion panel — the HOA's advisory review surface.
 *
 * The API is mocked. The rules pinned here are the batch's: the override
 * dropdowns must offer exactly the contract's vocabularies, a decision is
 * write-once, failures are explained without leaking reason codes, and residents
 * never see or call any of it.
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { triageCategories, triagePriorities, triageTrades } from '../api/generated/enums';
import { ApiError } from '../lib/api';
import { readTriageSuggestion, requestTriageSuggestion, decideTriageSuggestion } from '../lib/ai';
import { TriageSuggestion } from './TriageSuggestion';
const auth = vi.hoisted(() => ({ role: 'hoa_admin' }));
// The three calls are mocked; `isAiUnavailable` stays real, because it is the
// rule under test (a 503 AI_UNAVAILABLE is a quiet note, not an error).
vi.mock('../lib/ai', async (importOriginal) => ({
    ...(await importOriginal()),
    readTriageSuggestion: vi.fn(),
    requestTriageSuggestion: vi.fn(),
    decideTriageSuggestion: vi.fn(),
}));
vi.mock('../context/AuthContext', () => ({
    useAuth: () => ({ user: { id: 5, role: auth.role }, checking: false }),
}));
vi.mock('../context/EstateContext', () => ({
    useEstateScope: () => ({ estateId: 1, estate: { estate_id: 1, estate_name: 'Test Estate' } }),
}));
// `../lib/api` is deliberately NOT mocked: the real `ApiError` carries status,
// code and request_id, which is exactly what the panel branches on.
function suggestion(overrides = {}) {
    return {
        id: 11,
        complaint_id: 42,
        estate_id: 1,
        suggested_category: 'water',
        suggested_priority: 'urgent',
        suggested_trade: 'plumber',
        provider: 'fake',
        model: 'fake-model',
        prompt_version: 'triage-v1',
        decision: null,
        decided_by: null,
        decided_at: null,
        decided_category: null,
        decided_priority: null,
        decided_trade: null,
        created_at: '2026-10-01T07:00:00Z',
        ...overrides,
    };
}
function renderPanel(props = {}) {
    return render(<MemoryRouter>
      <TriageSuggestion estateId={1} complaintId={42} isAnonymous={props.isAnonymous ?? false}/>
    </MemoryRouter>);
}
function optionValues(select) {
    return Array.from(select.querySelectorAll('option')).map((option) => option.value);
}
beforeEach(() => {
    auth.role = 'hoa_admin';
    vi.mocked(readTriageSuggestion).mockRejectedValue(new ApiError(404, 'No triage suggestion exists for complaint 42.', 'RESOURCE_NOT_FOUND'));
    vi.mocked(requestTriageSuggestion).mockResolvedValue(suggestion());
    vi.mocked(decideTriageSuggestion).mockResolvedValue(suggestion({ decision: 'accepted' }));
});
describe('Triage suggestion — advisory copy and eligibility', () => {
    it('states that it is a suggestion for the HOA, with no automatic action implied', async () => {
        renderPanel();
        expect(await screen.findByText(/suggestion for the hoa/i)).toBeVisible();
        expect(screen.getByRole('heading', { name: 'AI triage' })).toBeVisible();
        expect(screen.getByText(/nothing is assigned or changed automatically/i)).toBeVisible();
        // It says what it is not: no promise of emergency response or auto-assignment.
        expect(screen.queryByText(/emergency response/i)).toBeNull();
        expect(screen.queryByText(/will be assigned automatically/i)).toBeNull();
    });
    it('refuses anonymous complaints without a retry', async () => {
        renderPanel({ isAnonymous: true });
        expect(await screen.findByText('AI triage is not available for anonymous complaints.')).toBeVisible();
        expect(screen.queryByRole('button', { name: /suggest triage/i })).toBeNull();
        expect(requestTriageSuggestion).not.toHaveBeenCalled();
    });
    it('never renders for a resident', async () => {
        auth.role = 'resident';
        // No API in a unit test: the drawer renders its own error state, which is fine.
        vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('offline'); }));
        const { ComplaintDrawer } = await import('./ComplaintDrawer');
        render(<MemoryRouter>
        <ComplaintDrawer complaintId={42} onClose={() => { }} onChanged={() => { }}/>
      </MemoryRouter>);
        await screen.findByRole('dialog');
        expect(screen.queryByText(/suggest triage/i)).toBeNull();
        expect(screen.queryByText(/triage/i)).toBeNull();
        expect(readTriageSuggestion).not.toHaveBeenCalled();
        expect(requestTriageSuggestion).not.toHaveBeenCalled();
    });
});
describe('Triage suggestion — requesting and reviewing', () => {
    it('requests a suggestion and shows the labels with the provider details', async () => {
        const user = userEvent.setup();
        renderPanel();
        await user.click(await screen.findByRole('button', { name: /suggest triage/i }));
        expect(await screen.findByText('Water')).toBeVisible();
        expect(screen.getByText('Urgent')).toBeVisible();
        expect(screen.getByText('Plumber')).toBeVisible();
        expect(screen.getByText(/fake · fake-model · triage-v1/)).toBeVisible();
        expect(requestTriageSuggestion).toHaveBeenCalledWith(1, 42);
    });
    it('links the suggested trade to the provider list filtered by that trade', async () => {
        const user = userEvent.setup();
        renderPanel();
        await user.click(await screen.findByRole('button', { name: /suggest triage/i }));
        const link = await screen.findByRole('link', { name: /plumber/i });
        expect(link).toHaveAttribute('href', '/app/providers?trade=plumber');
    });
    it('accepts the suggestion and becomes read-only', async () => {
        vi.mocked(decideTriageSuggestion).mockResolvedValue(suggestion({ decision: 'accepted', decided_by: 5, decided_at: '2026-10-02T09:00:00Z', decided_category: 'water', decided_priority: 'urgent', decided_trade: 'plumber' }));
        const user = userEvent.setup();
        renderPanel();
        await user.click(await screen.findByRole('button', { name: /suggest triage/i }));
        await user.click(screen.getByRole('button', { name: 'Accept' }));
        expect(await screen.findByText('Accepted')).toBeVisible();
        expect(screen.getByText(/user #5/)).toBeVisible();
        expect(screen.queryByRole('button', { name: 'Accept' })).toBeNull();
        expect(screen.queryByRole('button', { name: /suggest triage/i })).toBeNull();
        expect(decideTriageSuggestion).toHaveBeenCalledWith(1, 42, { decision: 'accepted' });
    });
    it('dismisses the suggestion and shows that it carried no labels', async () => {
        vi.mocked(decideTriageSuggestion).mockResolvedValue(suggestion({ decision: 'dismissed', decided_by: 5, decided_at: '2026-10-02T09:00:00Z' }));
        const user = userEvent.setup();
        renderPanel();
        await user.click(await screen.findByRole('button', { name: /suggest triage/i }));
        await user.click(screen.getByRole('button', { name: 'Dismiss' }));
        expect(await screen.findByText('Dismissed')).toBeVisible();
        expect(screen.getByText(/no labels/i)).toBeVisible();
        expect(decideTriageSuggestion).toHaveBeenCalledWith(1, 42, { decision: 'dismissed' });
    });
});
describe('Triage suggestion — override', () => {
    it('populates the override dropdowns from the generated vocabularies', async () => {
        const user = userEvent.setup();
        renderPanel();
        await user.click(await screen.findByRole('button', { name: /suggest triage/i }));
        await user.click(screen.getByRole('button', { name: /override/i }));
        expect(optionValues(screen.getByLabelText('Override category'))).toEqual([...triageCategories]);
        expect(optionValues(screen.getByLabelText('Override priority'))).toEqual([...triagePriorities]);
        expect(optionValues(screen.getByLabelText('Override trade'))).toEqual([
            '',
            ...triageTrades,
        ]);
    });
    it('requires at least one change before it can be saved', async () => {
        const user = userEvent.setup();
        renderPanel();
        await user.click(await screen.findByRole('button', { name: /suggest triage/i }));
        await user.click(screen.getByRole('button', { name: /override/i }));
        const save = screen.getByRole('button', { name: /save override/i });
        expect(save).toBeDisabled();
        await user.selectOptions(screen.getByLabelText('Override priority'), 'high');
        expect(save).toBeEnabled();
        await user.click(save);
        expect(decideTriageSuggestion).toHaveBeenCalledWith(1, 42, { decision: 'overridden', priority: 'high' });
    });
    it('treats a change back to the suggested value as no change', async () => {
        const user = userEvent.setup();
        renderPanel();
        await user.click(await screen.findByRole('button', { name: /suggest triage/i }));
        await user.click(screen.getByRole('button', { name: /override/i }));
        const priority = screen.getByLabelText('Override priority');
        await user.selectOptions(priority, 'high');
        expect(screen.getByRole('button', { name: /save override/i })).toBeEnabled();
        await user.selectOptions(priority, 'urgent');
        expect(screen.getByRole('button', { name: /save override/i })).toBeDisabled();
    });
    it('shows the override in the read-only view after saving', async () => {
        vi.mocked(decideTriageSuggestion).mockResolvedValue(suggestion({ decision: 'overridden', decided_by: 5, decided_at: '2026-10-02T09:00:00Z', decided_category: 'water', decided_priority: 'high', decided_trade: 'roofing' }));
        const user = userEvent.setup();
        renderPanel();
        await user.click(await screen.findByRole('button', { name: /suggest triage/i }));
        await user.click(screen.getByRole('button', { name: /override/i }));
        await user.selectOptions(screen.getByLabelText('Override trade'), 'roofing');
        await user.click(screen.getByRole('button', { name: /save override/i }));
        expect(await screen.findByText('Overridden')).toBeVisible();
        expect(screen.getByText('Decided labels: Water · High · Roofing')).toBeVisible();
        expect(screen.queryByLabelText('Override trade')).toBeNull();
    });
});
describe('Triage suggestion — failures', () => {
    it('explains an unavailable AI layer without leaking the reason code', async () => {
        vi.mocked(requestTriageSuggestion).mockRejectedValue(new ApiError(503, 'AI assist is unavailable for this request.', 'AI_UNAVAILABLE'));
        const user = userEvent.setup();
        renderPanel();
        await user.click(await screen.findByRole('button', { name: /suggest triage/i }));
        expect(await screen.findByText(/AI triage is unavailable right now/)).toBeVisible();
        expect(screen.getByText(/No triage was generated/)).toBeVisible();
        expect(screen.queryByText(/AI_UNAVAILABLE|provider_error|timeout|budget/)).toBeNull();
    });
    it('reports an already-decided suggestion and reloads it', async () => {
        vi.mocked(decideTriageSuggestion).mockRejectedValue(new ApiError(409, 'This suggestion has already been decided.', 'CONFLICT'));
        // The mount read finds nothing; the reload after the conflict finds the row
        // another administrator decided in the meantime.
        vi.mocked(readTriageSuggestion)
            .mockRejectedValueOnce(new ApiError(404, 'No triage suggestion exists for complaint 42.', 'RESOURCE_NOT_FOUND'))
            .mockResolvedValueOnce(suggestion({ decision: 'dismissed', decided_by: 9, decided_at: '2026-10-02T09:00:00Z' }));
        const user = userEvent.setup();
        renderPanel();
        await user.click(await screen.findByRole('button', { name: /suggest triage/i }));
        await user.click(screen.getByRole('button', { name: 'Accept' }));
        expect(await screen.findByText('This suggestion has already been decided.')).toBeVisible();
        await waitFor(() => expect(screen.getByText('Dismissed')).toBeVisible());
    });
    it('handles a forbidden estate without a retry button', async () => {
        vi.mocked(readTriageSuggestion).mockRejectedValue(new ApiError(403, 'You are not an administrator of this estate.', 'FORBIDDEN'));
        renderPanel();
        expect(await screen.findByText(/not an administrator/i)).toBeVisible();
        expect(screen.queryByRole('button', { name: /suggest triage/i })).toBeNull();
    });
    it('handles a missing complaint', async () => {
        vi.mocked(readTriageSuggestion).mockRejectedValue(new ApiError(404, 'Complaint with id 42 was not found.', 'RESOURCE_NOT_FOUND'));
        renderPanel();
        expect(await screen.findByText(/not found/i)).toBeVisible();
    });
    it('offers a retry when the network fails', async () => {
        vi.mocked(readTriageSuggestion).mockRejectedValue(new ApiError(0, 'Cannot reach the VALORA API.'));
        vi.mocked(requestTriageSuggestion).mockRejectedValueOnce(new ApiError(0, 'Cannot reach the VALORA API.'));
        const user = userEvent.setup();
        renderPanel();
        await user.click(await screen.findByRole('button', { name: /suggest triage/i }));
        expect(await screen.findByText(/cannot reach/i)).toBeVisible();
        expect(screen.getByRole('button', { name: /suggest triage/i })).toBeEnabled();
    });
    it('shows a stored decision when the panel opens', async () => {
        vi.mocked(readTriageSuggestion).mockResolvedValue(suggestion({ decision: 'overridden', decided_by: 5, decided_at: '2026-10-02T09:00:00Z', decided_category: 'noise', decided_priority: 'low', decided_trade: null }));
        renderPanel();
        expect(await screen.findByText('Overridden')).toBeVisible();
        expect(within(screen.getByText('Overridden').closest('div')).getByText(/user #5/)).toBeVisible();
    });
});
describe('Triage suggestion — keyboard and focus order', () => {
    it('requests, overrides and decides with the keyboard alone', async () => {
        const user = userEvent.setup();
        renderPanel();
        const suggest = await screen.findByRole('button', { name: /suggest triage/i });
        suggest.focus();
        expect(suggest).toHaveFocus();
        await user.keyboard('{Enter}');
        expect(await screen.findByText('Water')).toBeVisible();
        const override = screen.getByRole('button', { name: /override/i });
        override.focus();
        await user.keyboard('{Enter}');
        // Revealing the form moves focus into it, so a keyboard user is not dropped
        // back at the top of the panel.
        const category = screen.getByLabelText('Override category');
        expect(category).toHaveFocus();
        // The three dropdowns are labelled and reachable in order, then the two
        // form buttons — nothing in between steals focus. (Walking a native
        // `<select>` with the arrow keys is browser behaviour that jsdom does not
        // implement; the browser wiring check covers that with a real Chromium.)
        await user.tab();
        const priority = screen.getByLabelText('Override priority');
        expect(priority).toHaveFocus();
        await user.tab();
        const trade = screen.getByLabelText('Override trade');
        expect(trade).toHaveFocus();
        // While nothing has changed, Save is disabled — and a disabled control is
        // not in the tab order, so the keyboard lands on Cancel next. The hint under
        // the buttons says why.
        await user.tab();
        const save = screen.getByRole('button', { name: /save override/i });
        expect(save).toBeDisabled();
        expect(screen.getByRole('button', { name: /cancel/i })).toHaveFocus();
        expect(screen.getByText(/change at least one label/i)).toBeVisible();
        // Changing the labels is a real change, so Save becomes reachable and Enter
        // on it saves the override.
        await user.selectOptions(category, 'electrical');
        await user.selectOptions(priority, 'high');
        await user.selectOptions(trade, 'landscaping');
        expect(save).toBeEnabled();
        trade.focus();
        await user.tab();
        expect(save).toHaveFocus();
        await user.keyboard('{Enter}');
        expect(decideTriageSuggestion).toHaveBeenCalledWith(1, 42, {
            decision: 'overridden',
            category: 'electrical',
            priority: 'high',
            trade: 'landscaping',
        });
    });
});
