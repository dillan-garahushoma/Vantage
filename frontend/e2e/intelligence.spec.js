/** Browser wiring only: explicit API fixtures, separate from PostgreSQL acceptance. */
import { expect, test } from '@playwright/test';

async function intelligenceWorld(page, { denied = false, admin = true } = {}) {
    const user = { id: 1, email: 'fixture@example.com', full_name: 'Fixture member', role: admin ? 'hoa_admin' : 'resident' };
    const estate = { estate_id: 1, estate_name: 'Fictional Musgrave Complex', suburb: 'Musgrave', city: 'Durban',
        province: 'KwaZulu-Natal', membership_roles: [user.role], property_ids: [], is_estate_admin: admin, is_estate_provider: false };
    let saved = false;
    const briefing = () => ({ estate_id: 1, estate_name: estate.estate_name, role: user.role, source: 'stored_records',
        as_of: '2026-10-21T10:00:00Z', briefing_id: saved ? 4 : null, template_version: 'operational-v1', data_origin: 'demo',
        briefing: { headline: 'Stored operational records for Fictional Musgrave Complex.',
            body: admin ? 'There are 105 open complaints. Forecasts and savings are unavailable.' : 'Your own requests and published estate notices.', windowLabel: 'Current stored records',
            signalsReviewed: admin ? 105 : 0, sources: admin ? 3 : 1, avoidableZar: null }, recommendations: [],
        resident_view: admin ? null : { unit_issues: [], living_score_label: 'Not published', living_score_summary: '', community_notices: [] },
        operational_signals: admin ? { open_complaints: 105, work_orders_in_flight: 0, unresolved_incidents: 0 } : null,
        limitations: ['Counts describe stored records, not a weekly activity total.'] });
    await page.route(/https:\/\/fonts\.(googleapis|gstatic)\.com\//, route => route.abort());
    await page.addInitScript((value) => {
        localStorage.setItem('valora.token', 'fixture-token');
        localStorage.setItem('valora.user', JSON.stringify(value));
        localStorage.setItem('valora.estate', '1');
    }, user);
    await page.route('**/api/v1/**', async route => {
        const path = new URL(route.request().url()).pathname;
        if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 204 });
        if (path === '/api/v1/auth/me') return route.fulfill({ json: user });
        if (path === '/api/v1/auth/estates') return route.fulfill({ json: { estates: [estate] } });
        if (path === '/api/v1/analytics/intelligence/ask/stream') return route.fulfill({ contentType: 'text/event-stream', body: 'data: {"delta":"No stored Living Score snapshot is available for this estate."}\n\ndata: [DONE]\n\n' });
        if (path === '/api/v1/analytics/intelligence/ask') return route.fulfill({ json: {
            summary: 'No stored Living Score snapshot is available for this estate.',
            evidence: ['complaints [estate_id=1]: 105 open.'], recommendation: 'Review the cited records.', related: [], source: 'estate-domain' } });
        if (path === '/api/v1/analytics/intelligence/briefing/generate') {
            saved = true;
            return route.fulfill({ status: 201, json: briefing() });
        }
        if (path === '/api/v1/analytics/intelligence') return denied
            ? route.fulfill({ status: 403, json: { detail: { code: 'FORBIDDEN', message: 'Estate access denied.' } } })
            : route.fulfill({ json: briefing() });
        return route.fulfill({ json: { items: [], total: 0, page: 1, size: 20, pages: 0 } });
    });
}

test('shows measured counts, saves a dated briefing and asks the authenticated API', async ({ page }) => {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await intelligenceWorld(page);
    await page.goto('/intelligence');
    await expect(page.getByText('105', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Save current briefing' }).click();
    await expect(page.getByText(/Saved briefing ·/)).toBeVisible();
    await expect(page.getByText(/Counts are frozen at the briefing date/)).toBeVisible();
    await page.getByRole('button', { name: 'What is the operational risk summary for this week?' }).click();
    await expect(page.getByText('No stored Living Score snapshot is available for this estate.')).toBeVisible();
    expect(errors).toEqual([]);
});

test('a backend denial never displays fictional pump or savings claims', async ({ page }) => {
    await intelligenceWorld(page, { denied: true });
    await page.goto('/intelligence');
    await expect(page.getByText('Briefing unavailable')).toBeVisible();
    await expect(page.getByText('Estate access denied.')).toBeVisible();
    await expect(page.getByText(/Pool Pump 02/)).toHaveCount(0);
    await expect(page.getByText('R42,000')).toHaveCount(0);
});

test('residents see their personal assistant without management aggregates or save controls', async ({ page }) => {
    await intelligenceWorld(page, { admin: false });
    await page.goto('/intelligence');
    await expect(page.getByText('No open maintenance issues logged for your unit.')).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Ask VALORA a question' })).toBeEnabled();
    await expect(page.getByText('105', { exact: true })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Save current briefing' })).toHaveCount(0);
});
