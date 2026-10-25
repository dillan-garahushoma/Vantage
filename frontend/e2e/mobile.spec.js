import { expect, test } from '@playwright/test';
/**
 * The mobile sweep: nothing may push the page sideways at 390 × 844.
 *
 * The API is mocked, deliberately. This spec is about layout, so it must be able
 * to render every screen — including the administrator and provider ones — without
 * a database, a seed or an account, and it must fail for a layout reason only.
 *
 * The measurement is the document's own `scrollWidth` against the viewport, plus
 * a list of the elements whose right edge is past the viewport, so a failure says
 * *what* is too wide rather than only that something is.
 */
const VIEWPORT = { width: 390, height: 844 };
const ESTATE = {
    estate_id: 1,
    estate_name: 'Ridge Close Estate',
    suburb: 'Centurion',
    city: 'Tshwane',
    province: 'Gauteng',
    membership_roles: ['resident', 'hoa_admin'],
    property_ids: [10, 11],
    is_estate_admin: true,
    is_estate_provider: false,
};
const ADMIN_USER = {
    id: 1,
    email: 'admin@example.co.za',
    full_name: 'Nomvula Dlamini',
    role: 'hoa_admin',
    unit_no: 'A-1',
    email_verified: true,
    hoa_approved: true,
};
/** Every endpoint the app calls, with a shape the screens can actually render. */
function fixture(path, method) {
    if (path === '/api/v1/auth/me')
        return ADMIN_USER;
    if (path === '/api/v1/auth/estates')
        return { estates: [ESTATE] };
    if (path === '/api/v1/analytics/health-brief') {
        return {
            source: 'template',
            insight_id: null,
            ai_unavailable_reason: null,
            data_origin: 'demo',
            snapshot_id: 3,
            as_of: '2026-10-01T06:30:00Z',
            generated_at: null,
            provider: null,
            model: null,
            prompt_version: null,
            facts: {
                engine_version: '1.0.0',
                as_of: '2026-10-01T06:30:00Z',
                measured_weight: '80',
                window_days: 90,
                compared_days: [30, 90],
                score_min: 0,
                score_max: 100,
                overall: {
                    score: '72.5',
                    status: 'scored',
                    delta_30d: '+1.5',
                    delta_30d_abs: '1.0',
                    delta_90d: '-4.0',
                    delta_90d_abs: '-2.5',
                },
                components: [
                    {
                        key: 'resolution',
                        weight_pct: '35',
                        status: 'measured',
                        score: '81.2',
                        delta_30d: '+2.0',
                        delta_30d_abs: '1.4',
                        delta_90d: null,
                        delta_90d_abs: null,
                        inputs: { median_hours: 18, resolved: 12 },
                    },
                ],
            },
            output: null,
        };
    }
    if (path === '/api/v1/analytics/living-score') {
        return {
            estate_id: 1,
            overall_score: '72.5',
            status: 'scored',
            as_of: '2026-10-01T06:30:00Z',
            engine_version: '1.0.0',
            data_origin: 'demo',
            components: [
                { key: 'resolution', weight_pct: '35', score: '81.2', status: 'measured' },
                { key: 'complaints', weight_pct: '20', score: '60.0', status: 'measured' },
            ],
        };
    }
    if (path === '/api/v1/complaints/stats') {
        return {
            total: 24,
            by_status: { resolved: 18, in_progress: 3, submitted: 3 },
            by_category: { water: 6 },
            resolution_rate_pct: '75.0',
            avg_resolution_hours: '38.4',
        };
    }
    if (path === '/api/v1/complaints') {
        return {
            items: [
                {
                    id: 7,
                    user_id: null,
                    estate_id: 1,
                    unit_id: 10,
                    category: 'water',
                    description: 'Sewage overflow at the corner of Block C — standing water across the whole driveway and the smell reaches the units.',
                    priority: 'urgent',
                    is_anonymous: false,
                    status: 'in_progress',
                    assigned_to: null,
                    reviewed_at: null,
                    assigned_at: null,
                    started_at: null,
                    resolved_at: null,
                    created_at: '2026-10-01T08:00:00Z',
                    updated_at: null,
                },
            ],
            total: 24,
            page: 1,
            size: 12,
            pages: 2,
        };
    }
    if (path === '/api/v1/announcements') {
        return {
            items: [
                {
                    id: 1,
                    estate_id: 1,
                    title: 'Water interruption on Tuesday',
                    message: 'The municipality will interrupt supply between 08:00 and 16:00 while the main line is replaced.',
                    created_by: 1,
                    expires_at: null,
                    created_at: '2026-10-01T08:00:00Z',
                    updated_at: null,
                },
            ],
            total: 1,
            page: 1,
            size: 4,
            pages: 1,
        };
    }
    if (path === '/api/v1/properties') {
        return {
            items: [
                {
                    id: 10,
                    estate_id: 1,
                    unit_no: 'A-101',
                    complex_name: 'Ridge Close',
                    street_address: '12 Ridge Close',
                    suburb: 'Centurion',
                    size_m2: '96',
                    bedrooms: 3,
                    bathrooms: 2,
                },
            ],
            total: 24,
            page: 1,
            size: 100,
            pages: 1,
        };
    }
    if (path === '/api/v1/providers' || path === '/api/v1/providers/me') {
        const provider = {
            id: 3,
            full_name: 'Sipho Mokoena',
            trade: 'plumbing',
            phone: '082 000 0000',
            email: 'sipho@example.co.za',
            avg_rating: '4.50',
            total_reviews: 12,
            verified: true,
            emergency_available: true,
        };
        if (path === '/api/v1/providers/me')
            return provider;
        return { items: [provider], total: 1, page: 1, size: 20, pages: 1 };
    }
    if (path === '/api/v1/work-orders' || path === '/api/v1/work-orders/mine') {
        return {
            items: [
                {
                    id: 42,
                    complaint_id: 7,
                    provider_id: 3,
                    assigned_at: '2026-10-01T08:00:00Z',
                    resolved_at: null,
                    job_cost: '1250.00',
                    resident_rating: null,
                    completion_notes: null,
                    status: 'in_progress',
                    estimated_completion_date: '2026-10-08T08:00:00Z',
                    actual_completion_date: null,
                    created_at: '2026-10-01T08:00:00Z',
                    updated_at: null,
                },
            ],
            total: 1,
            page: 1,
            size: 20,
            pages: 1,
        };
    }
    if (path === '/api/v1/estates/profile') {
        return {
            estate_id: 1,
            name: 'Ridge Close Estate',
            suburb: 'Centurion',
            city: 'Tshwane',
            province: 'Gauteng',
            description: 'A 24-unit complex with a single monitored gate.',
            is_demo: true,
            is_public: true,
            show_living_score: true,
        };
    }
    if (path === '/api/v1/estates/photos') {
        return [
            {
                photo_id: 5,
                public_id: 'pub1',
                caption: 'The pool at dusk',
                position: 0,
                width: 1920,
                height: 1280,
                bytes: 184320,
                created_at: '2026-10-01T08:00:00Z',
            },
        ];
    }
    if (path === '/api/v1/join-codes/current') {
        return {
            id: 1,
            estate_id: 1,
            code: 'ABCD2EFGH3',
            expires_at: '2026-11-01T08:00:00Z',
            created_at: '2026-10-01T08:00:00Z',
        };
    }
    if (path === '/api/v1/memberships') {
        return {
            items: [
                {
                    membership_id: 11,
                    role: 'resident',
                    full_name: 'Thandi Nkosi',
                    email: 'thandi@example.co.za',
                    unit_no: 'A-101',
                    joined_at: '2026-09-02T08:00:00Z',
                },
                {
                    membership_id: 12,
                    role: 'service_provider',
                    full_name: 'Sipho Mokoena',
                    email: 'sipho@example.co.za',
                    unit_no: null,
                    joined_at: '2026-09-14T08:00:00Z',
                },
            ],
            total: 2,
            page: 1,
            size: 20,
            pages: 1,
        };
    }
    if (path === '/api/v1/residency-requests/mine')
        return [];
    if (path === '/api/v1/residency-requests/pending-count')
        return { pending: 2 };
    if (path === '/api/v1/residency-requests') {
        return {
            items: [
                {
                    request_id: 31,
                    estate_id: 1,
                    estate_name: 'Ridge Close Estate',
                    unit_no: 'A-101',
                    status: 'pending',
                    applicant_name: 'Thandi Nkosi',
                    applicant_email: 'thandi@example.co.za',
                    applicant_phone: '082 000 0000',
                    note: 'Lease starts 1 Nov',
                    created_at: '2026-10-13T09:30:00Z',
                    decided_at: null,
                    decision_note: null,
                },
            ],
            total: 1,
            page: 1,
            size: 20,
            pages: 1,
        };
    }
    if (path === '/api/v1/public/estates') {
        return {
            items: [
                {
                    estate_id: 1,
                    name: 'Ridge Close Estate',
                    suburb: 'Centurion',
                    city: 'Tshwane',
                    province: 'Gauteng',
                    description: 'A 24-unit complex with a single monitored gate.',
                    unit_count: 24,
                    cover_photo_public_id: 'pub1',
                },
            ],
            total: 1,
            page: 1,
            size: 12,
            pages: 1,
        };
    }
    const publicDetail = /^\/api\/v1\/public\/estates\/(\d+)$/.exec(path);
    if (publicDetail) {
        const estateId = Number(publicDetail[1]);
        // Estate 2 publishes a full gallery, so the sweep measures the multi-photo
        // mosaic too — not only the single-photo case, which is the easy one — and
        // estate 3 publishes more than the mosaic can hold, so the overflow tile and
        // its count are measured at 390px as well.
        const count = estateId === 3 ? 12 : estateId === 2 ? 5 : 1;
        return {
            estate_id: estateId,
            name: 'Ridge Close Estate',
            suburb: 'Centurion',
            city: 'Tshwane',
            province: 'Gauteng',
            description: 'A 24-unit complex with a single monitored gate.',
            unit_count: 24,
            photos: Array.from({ length: count }, (_, index) => ({
                public_id: `pub${index + 1}`,
                caption: index === 0 ? 'The pool at dusk' : null,
            })),
            living_score: {
                overall_score: '72.5',
                status: 'scored',
                as_of: '2026-10-01T06:30:00Z',
                engine_version: '1.0.0',
                data_origin: 'demo',
            },
        };
    }
    if (path === '/api/v1/public/photos/pub1') {
        return undefined;
    }
    if (method === 'GET') {
        // An unlisted collection is an empty one: the state still has to lay out.
        return { items: [], total: 0, page: 1, size: 20, pages: 0 };
    }
    return {};
}
async function mockApi(page, options = {}) {
    // The webfonts come from a CDN, so a measurement taken while they load is not
    // repeatable (and cannot run offline). The fallback stack lays out the same way
    // structurally, which is what this spec is measuring.
    await page.route('https://fonts.googleapis.com/**', (route) => route.abort());
    await page.route('https://fonts.gstatic.com/**', (route) => route.abort());
    await page.addInitScript(([user, estates]) => {
        localStorage.setItem('valora.token', 'e2e-token');
        localStorage.setItem('valora.user', JSON.stringify(user));
        localStorage.setItem('valora.estate', '1');
        // The estate scope is resolved from the API; this only short-circuits the
        // first paint so a measurement is never taken mid-redirect.
        void estates;
    }, [ADMIN_USER, options.estates ?? [ESTATE]]);
    await page.route('**/api/v1/**', async (route) => {
        const url = new URL(route.request().url());
        const method = route.request().method();
        if (url.pathname === '/api/v1/auth/estates') {
            const estates = options.estates ?? [ESTATE];
            await route.fulfill({ json: { estates }, status: 200 });
            return;
        }
        if (url.pathname === '/api/v1/auth/me') {
            await route.fulfill({ json: { ...ADMIN_USER, role: options.role ?? ADMIN_USER.role } });
            return;
        }
        // Photos are images, not JSON, and the layout must be measured with the
        // image failing rather than with a JSON body painted as one.
        if (url.pathname.startsWith('/api/v1/public/photos/')) {
            await route.fulfill({ status: 404, body: '' });
            return;
        }
        const body = fixture(url.pathname, method);
        if (body === undefined) {
            await route.fulfill({ status: 404, json: { detail: 'not mocked' } });
            return;
        }
        await route.fulfill({ json: body });
    });
}
/**
 * The elements reaching furthest past the viewport, widest first, so a failure
 * names the culprit instead of only the number. Elements that legitimately scroll
 * inside their own container (a table in `overflow-x-auto`) are still listed — the
 * point is to see what is *outside* a scroll container by looking at the chain.
 */
async function overflowing(page) {
    return page.evaluate(() => {
        const limit = document.documentElement.clientWidth;
        const describe = (element) => {
            const box = element.getBoundingClientRect();
            const tag = element.tagName.toLowerCase();
            const cls = (element.getAttribute('class') ?? '')
                .split(/\s+/)
                .filter(Boolean)
                .slice(0, 3)
                .join('.');
            return {
                element,
                label: `${tag}${element.id ? `#${element.id}` : ''}.${cls} left=${Math.round(box.left)} width=${Math.round(box.width)} right=${Math.round(box.right)}`,
                right: Math.max(box.right, -box.left),
            };
        };
        const offenders = Array.from(document.querySelectorAll('*'))
            .filter((element) => {
            const box = element.getBoundingClientRect();
            if (box.width === 0 || box.height === 0)
                return false;
            return box.right > limit + 1 || box.left < -1;
        })
            .map(describe)
            .sort((a, b) => b.right - a.right);
        const lines = offenders.slice(0, 10).map((item) => item.label);
        // The widest element is often a wrapper; the deepest one is the leaf that
        // actually refuses to shrink. Walk up from the deepest and report each
        // ancestor's width, so the failure says where the minimum width comes from.
        const depthOf = (element) => {
            let depth = 0;
            for (let node = element.parentElement; node; node = node.parentElement)
                depth += 1;
            return depth;
        };
        const deepest = [...offenders].sort((a, b) => depthOf(b.element) - depthOf(a.element))[0];
        if (deepest) {
            lines.push(`--- deepest offender: ${(deepest.element.textContent ?? '').trim().slice(0, 60)}`);
            let node = deepest.element;
            for (let depth = 0; node && depth < 10; depth += 1) {
                const style = getComputedStyle(node);
                lines.push(`  ${describe(node).label} min-width=${style.minWidth} overflow-x=${style.overflowX} display=${style.display}`);
                node = node.parentElement;
            }
            lines.push(`body width=${Math.round(document.body.getBoundingClientRect().width)} viewport=${limit}`);
        }
        return lines;
    });
}
async function measure(page, path, options = {}) {
    await mockApi(page, path === '/provider/work' ? { ...options, role: 'service_provider' } : options);
    await page.setViewportSize(VIEWPORT);
    await page.goto(path);
    // Settle: data loads are mocked, so this is about layout, not waiting on I/O.
    await page.waitForLoadState('networkidle');
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(150);
    // Measuring a 404 proves only that the 404 has no overflow. The route under
    // test must render its own expected landmark first.
    const expectedHeadings = {
        '/': /see how your estate is cared for/i,
        '/estates': /find a complex/i,
        '/estates/1': /^ridge close estate$/i,
        '/estates/2': /^ridge close estate$/i,
        '/estates/3': /^ridge close estate$/i,
        '/provider/work': /my work/i,
    };
    if (expectedHeadings[path]) {
        await expect(page.getByRole('heading', { name: expectedHeadings[path] })).toBeVisible();
    }
    const offenders = await overflowing(page);
    const widths = await page.evaluate(() => ({
        scroll: document.documentElement.scrollWidth,
        client: document.documentElement.clientWidth,
    }));
    // A plain throw, not an expect: the message has to carry the element list, and
    // that is the whole reason this spec exists rather than a screenshot comparison.
    if (widths.scroll > widths.client) {
        throw new Error([
            `${path} overflows at ${VIEWPORT.width}px: ${widths.scroll} > ${widths.client}`,
            ...offenders,
        ].join('\n'));
    }
}
const ROUTES = [
    '/',
    '/estates',
    '/estates/1',
    '/estates/2',
    '/estates/3',
    '/login',
    '/register',
    '/app',
    '/app/complaints',
    '/app/work-orders',
    '/app/announcements',
    '/app/properties',
    '/app/providers',
    '/request-access',
    '/admin/setup',
    '/admin/residency',
    '/admin/members',
    '/provider/work',
];
test.describe('mobile sweep at 390px', () => {
    for (const path of ROUTES) {
        test(`${path} does not scroll sideways`, async ({ page }) => {
            await measure(page, path);
        });
    }
    test('a resident with no estate sees the join screen within the viewport', async ({ page }) => {
        await measure(page, '/join', { estates: [], role: 'resident' });
    });
    test('a provider with no estate sees the waiting screen within the viewport', async ({ page }) => {
        await measure(page, '/provider/waiting', { estates: [], role: 'service_provider' });
    });
});
