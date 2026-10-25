/**
 * The dashboard Living Score panel.
 *
 * Two things these tests exist to hold down:
 *
 * 1. **Nothing is calculated in React.** Every figure rendered is the one the API
 *    stored, formatted — `82.76` is shown as `82.8`, never re-rounded into a
 *    different number, and the component list is whatever the response carried,
 *    not a hard-coded five.
 * 2. **"No data" is words, never a zero.** A 404 (never scored) and an
 *    `insufficient_data` snapshot are both honest states with an explanation, and
 *    neither invents a number.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ApiError } from '../lib/api';
import { LivingScorePanel } from './LivingScore';
function component(overrides = {}) {
    return {
        key: 'resolution',
        label: 'Resolution speed',
        weight: '0.30',
        status: 'measured',
        score: '91.2',
        inputs: {},
        benchmark: '1 day or less scores 100; 30 days or more scores 0.',
        contribution: null,
        lost_points: null,
        explanation: '9 complaints resolved, averaging 2.4 days.',
        recommendation: null,
        ...overrides,
    };
}
function snapshot(overrides = {}) {
    return {
        id: 12,
        estate_id: 1,
        engine_version: '1.0.0',
        as_of: '2026-10-05T09:00:00Z',
        window_start: '2026-07-07T09:00:00Z',
        calculated_at: '2026-10-04T09:00:02Z',
        status: 'scored',
        overall_score: '82.76',
        measured_weight: '1.00',
        is_demo: false,
        components: [
            component(),
            component({ key: 'frequency', label: 'Complaint frequency', weight: '0.25', score: '74.5' }),
            component({ key: 'security', label: 'Security', weight: '0.20', score: '100' }),
            component({ key: 'satisfaction', label: 'Resident satisfaction', weight: '0.15', score: '68.4' }),
            component({
                key: 'infrastructure',
                label: 'Maintenance completion',
                weight: '0.10',
                score: '55.1',
            }),
        ],
        drivers: [],
        ...overrides,
    };
}
function renderPanel(props = {}) {
    return render(<LivingScorePanel snapshot={null} loading={false} error={null} {...props}/>);
}
describe('LivingScorePanel — the stored snapshot', () => {
    it('renders the stored figures verbatim: score, status, components, versions and dates', () => {
        renderPanel({ snapshot: snapshot() });
        // The stored value, formatted once for display (en-ZA) — not re-rounded to a band.
        expect(screen.getByText('82,8')).toBeVisible();
        expect(screen.getByText('Healthy')).toBeVisible();
        // All five components, each with its own stored sub-score and weight.
        expect(screen.getByText('Resolution speed')).toBeVisible();
        expect(screen.getByText('91,2 / 100')).toBeVisible();
        expect(screen.getByText('Complaint frequency')).toBeVisible();
        expect(screen.getByText('74,5 / 100')).toBeVisible();
        expect(screen.getByText('Security')).toBeVisible();
        expect(screen.getByText('100 / 100')).toBeVisible();
        expect(screen.getByText('Resident satisfaction')).toBeVisible();
        expect(screen.getByText('68,4 / 100')).toBeVisible();
        expect(screen.getByText('Maintenance completion')).toBeVisible();
        expect(screen.getByText('55,1 / 100')).toBeVisible();
        expect(screen.getByText('30% of the score')).toBeVisible();
        expect(screen.getByText('10% of the score')).toBeVisible();
        // Provenance: when it was calculated for, by which engine, and when stored.
        expect(screen.getByText('05 Oct 2026')).toBeVisible();
        expect(screen.getByText('04 Oct 2026')).toBeVisible();
        expect(screen.getByText('1.0.0')).toBeVisible();
    });
    it('shows the components the response carried, and only those', () => {
        renderPanel({
            snapshot: snapshot({
                components: [component({ key: 'security', label: 'Security', score: '100' })],
            }),
        });
        expect(screen.getByText('Security')).toBeVisible();
        expect(screen.queryByText('Resolution speed')).toBeNull();
        expect(screen.queryByText('Maintenance completion')).toBeNull();
    });
    it('never labels operational score data as demonstration data', () => {
        const { unmount } = renderPanel({ snapshot: snapshot({ is_demo: true }) });
        expect(screen.queryByText('Demo data')).toBeNull();
        unmount();
        renderPanel({ snapshot: snapshot({ is_demo: false }) });
        expect(screen.queryByText('Demo data')).toBeNull();
    });
    it('surfaces the engine’s own advice for the factors that cost the most', () => {
        renderPanel({
            snapshot: snapshot({
                drivers: [
                    component({
                        key: 'infrastructure',
                        label: 'Maintenance completion',
                        recommendation: 'Follow up the work orders that are still open or stalled.',
                    }),
                ],
            }),
        });
        expect(screen.getByText('Where to look next')).toBeVisible();
        expect(screen.getByText(/Follow up the work orders that are still open or stalled/)).toBeVisible();
    });
});
describe('LivingScorePanel — no score yet', () => {
    it('reports a 404 as "not scored yet" and never as a zero', () => {
        renderPanel({
            error: new ApiError(404, 'No Living Score has been calculated for this estate yet.', 'NOT_FOUND'),
        });
        expect(screen.getByText('Not enough data yet')).toBeVisible();
        expect(screen.getByText(/has not been scored yet/i)).toBeVisible();
        expect(screen.queryByText('0')).toBeNull();
        expect(screen.getByText('Not scored')).toBeVisible();
    });
    it('shows the published weights so the panel is useful while it waits', () => {
        renderPanel({
            error: new ApiError(404, 'No Living Score has been calculated for this estate yet.'),
        });
        expect(screen.getByText('Complaint resolution time')).toBeVisible();
        expect(screen.getByText('Security incidents')).toBeVisible();
        expect(screen.getByText('Resident satisfaction')).toBeVisible();
        expect(screen.getAllByText('awaiting data')).toHaveLength(5);
    });
    it('explains an insufficient_data snapshot with the engine’s own reason', () => {
        renderPanel({
            snapshot: snapshot({
                status: 'insufficient_data',
                overall_score: null,
                measured_weight: '0.60',
                components: [
                    component({
                        key: 'resolution',
                        label: 'Resolution speed',
                        status: 'insufficient_data',
                        score: null,
                        explanation: 'Only 1 complaint(s) were resolved in the window; at least 3 are needed.',
                    }),
                    component({ key: 'security', label: 'Security', score: '100' }),
                ],
            }),
        });
        expect(screen.getByText('Not enough data yet')).toBeVisible();
        expect(screen.getByText(/Insufficient data/)).toBeVisible();
        expect(screen.getByText(/60% of the score's weight is measurable/)).toBeVisible();
        expect(screen.getByText(/Only 1 complaint\(s\) were resolved in the window/)).toBeVisible();
        // The measurable component is still shown honestly, and the unmeasured one
        // is described in words rather than as a zero.
        expect(screen.getByText('100 / 100')).toBeVisible();
        expect(screen.getByText('no evidence yet')).toBeVisible();
        expect(screen.queryByText('0 / 100')).toBeNull();
    });
    it('does not pretend a snapshot’s status is scored when the number is missing', () => {
        renderPanel({
            snapshot: snapshot({ status: 'scored', overall_score: null }),
        });
        expect(screen.getByText('Not enough data yet')).toBeVisible();
        expect(screen.queryByText('Healthy')).toBeNull();
    });
});
describe('LivingScorePanel — loading and failure', () => {
    it('shows a loading state before the snapshot arrives', () => {
        renderPanel({ loading: true });
        expect(screen.getByText(/Loading the Living Score/)).toBeVisible();
    });
    it('shows the server’s message and reference when the request failed', async () => {
        const onRetry = vi.fn();
        const user = userEvent.setup();
        renderPanel({
            error: new ApiError(503, 'The scoring service is unavailable.', 'SERVICE_UNAVAILABLE', 'req-503'),
            onRetry,
        });
        expect(screen.getByText('Could not load the Living Score')).toBeVisible();
        expect(screen.getByText('The scoring service is unavailable.')).toBeVisible();
        expect(screen.getByText(/req-503/)).toBeVisible();
        await user.click(screen.getByRole('button', { name: /try again/i }));
        expect(onRetry).toHaveBeenCalledTimes(1);
    });
    it('offers the "check again" affordance on the never-scored state', async () => {
        const onRetry = vi.fn();
        const user = userEvent.setup();
        renderPanel({ error: new ApiError(404, 'Not scored yet.'), onRetry });
        await user.click(screen.getByRole('button', { name: /check again/i }));
        expect(onRetry).toHaveBeenCalledTimes(1);
    });
});
