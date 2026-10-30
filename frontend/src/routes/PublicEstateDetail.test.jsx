/**
 * The published estate page — the one screen that shows a single complex to
 * someone without an account.
 *
 * Two things are worth pinning here. First, that the page shows only what the
 * API publishes: no price, no rating, no coordinate, and no score when the
 * administrator did not opt in. Second, that the photographs — the reason anyone
 * opens this page — are reachable and drivable from a keyboard, because a
 * full-screen image viewer is a modal dialog whether or not it says so.
 */
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../lib/api';
import { PublicEstateDetail as EstatePage } from './PublicEstateDetail';
const mocks = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock('../lib/publicDirectory', () => ({
    getPublicEstate: mocks.get,
    publicPhotoUrl: (id, size) => `http://api.test/photo/${id}?size=${size}`,
    photoAlt: (name, caption) => caption ?? `Photo of ${name}`,
}));
vi.mock('../context/AuthContext', () => ({
    useAuth: () => ({ user: null }),
}));
function detail(overrides = {}) {
    return {
        estate_id: 1,
        name: 'Ridge Close',
        suburb: 'Centurion',
        city: 'Tshwane',
        province: 'Gauteng',
        description: 'A 24-unit complex with a single monitored gate.',
        unit_count: 24,
        photos: [
            { public_id: 'p1', caption: 'The pool at dusk' },
            { public_id: 'p2', caption: null },
            { public_id: 'p3', caption: null },
            { public_id: 'p4', caption: null },
            { public_id: 'p5', caption: null },
        ],
        living_score: {
            overall_score: '72.5',
            status: 'scored',
            as_of: '2026-10-01T06:30:00Z',
            engine_version: '1.0.0',
            data_origin: 'demo',
        },
        ...overrides,
    };
}
function renderPage() {
    return render(<MemoryRouter initialEntries={['/estates/1']}>
      <Routes>
        <Route path="/estates/:id" element={<EstatePage />}/>
        <Route path="/register" element={<p>Resident account route</p>}/>
      </Routes>
    </MemoryRouter>);
}
beforeEach(() => {
    mocks.get.mockReset();
    window.sessionStorage.clear();
});
describe('PublicEstateDetail', () => {
    it('does not invent security services, HOA names or amenities absent from the API', async () => {
        mocks.get.mockResolvedValue(detail({ description: null, living_score: null, unit_count: 3 }));
        renderPage();
        expect(await screen.findByRole('heading', { level: 1, name: 'Ridge Close' })).toBeVisible();
        expect(screen.queryByText(/24\/7|verified visitor logging|monitored estate security|managed by ridge close hoa|communal infrastructure/i)).toBeNull();
        expect(screen.getByText(/administrator has not written a description yet/i)).toBeVisible();
    });
    it('does not turn an unscored published snapshot into a zero in the highlights', async () => {
        mocks.get.mockResolvedValue(detail({ living_score: { ...detail().living_score, overall_score: null, status: 'insufficient_data' } }));
        renderPage();
        await screen.findByRole('heading', { level: 1, name: 'Ridge Close' });
        expect(screen.queryByText(/Living Score (0\.0|NaN) \/ 100/)).toBeNull();
    });
    it('leads with what was published, and invents nothing to fill the gaps', async () => {
        mocks.get.mockResolvedValue(detail());
        renderPage();
        expect(await screen.findByRole('heading', { level: 1, name: 'Ridge Close' })).toBeVisible();
        expect(screen.getByText(/Centurion, Tshwane, Gauteng/)).toBeVisible();
        expect(screen.getByText('24 units')).toBeVisible();
        expect(screen.getByText('5 photographs')).toBeVisible();
        expect(screen.getByText(/a 24-unit complex/i)).toBeVisible();
        // The one trust figure the product has, as a chip beside the title, anchored
        // to the card that explains it.
        // 72.5 is the shared display band's "Watch", not its "Healthy": the band label
        // comes from display.js so the same number reads the same way everywhere.
        expect(screen.getByRole('link', { name: /living score 72\.5 watch/i })).toHaveAttribute('href', '#living-score');
        // A property directory is under real pressure to invent a price and a rating.
        // This one has neither, so it must not look like it does.
        expect(screen.queryByText(/per night|per month|for sale|★|out of 5/i)).toBeNull();
    });
    it('shows the published score with its own provenance and no breakdown', async () => {
        mocks.get.mockResolvedValue(detail());
        renderPage();
        const heading = await screen.findByRole('heading', { name: 'Living Score' });
        const card = within(heading.closest('section'));
        expect(card.getByText(/72\.5/)).toBeVisible();
        expect(card.getByText('Watch')).toBeVisible();
        expect(card.queryByText('Demo data')).toBeNull();
        expect(card.getByText('1.0.0')).toBeVisible();
        expect(card.getByText(/Published by this estate’s administrator/i)).toBeVisible();
    });
    it('says nothing about a score the estate did not publish', async () => {
        mocks.get.mockResolvedValue(detail({ living_score: null }));
        renderPage();
        expect(await screen.findByRole('heading', { level: 1, name: 'Ridge Close' })).toBeVisible();
        expect(screen.queryByRole('heading', { name: 'Living Score' })).toBeNull();
        expect(screen.queryByRole('link', { name: 'Living Score' })).toBeNull();
        expect(screen.queryByText('Watch')).toBeNull();
    });
    it('opens the photographs in a viewer a keyboard can drive, and gives focus back', async () => {
        mocks.get.mockResolvedValue(detail());
        const user = userEvent.setup();
        renderPage();
        const tile = await screen.findByRole('button', { name: /open photograph 1 of 5/i });
        await user.click(tile);
        const dialog = screen.getByRole('dialog', { name: /photographs of ridge close/i });
        expect(within(dialog).getByText('1 of 5')).toBeVisible();
        // The viewer asks for the stored full image, not the tile's thumbnail.
        expect(within(dialog).getByAltText('The pool at dusk')).toHaveAttribute('src', 'http://api.test/photo/p1?size=full');
        await user.keyboard('{ArrowRight}');
        expect(within(dialog).getByText('2 of 5')).toBeVisible();
        // Backwards off the first photograph wraps to the last: a viewer that stops
        // dead at either end hides the photographs it is supposed to show.
        await user.keyboard('{ArrowLeft}{ArrowLeft}');
        expect(within(dialog).getByText('5 of 5')).toBeVisible();
        await user.keyboard('{Escape}');
        expect(screen.queryByRole('dialog')).toBeNull();
        expect(tile).toHaveFocus();
    });
    it('navigates within the page, and states what it will never publish', async () => {
        mocks.get.mockResolvedValue(detail());
        renderPage();
        await screen.findByRole('heading', { level: 1, name: 'Ridge Close' });
        const nav = screen.getByRole('navigation', { name: /sections of this complex/i });
        for (const label of ['Photographs', 'About', 'Location', 'Living Score', 'Joining']) {
            expect(within(nav).getByRole('link', { name: label })).toBeInTheDocument();
        }
        expect(within(nav).getByRole('link', { name: 'Photographs' })).toHaveAttribute('href', '#photos');
        // Two bars are pinned to the top of this page, so a jump has to clear them.
        expect(document.querySelector('#about')?.className).toMatch(/scroll-mt-/);
        expect(screen.getByText(/street addresses and unit numbers/i)).toBeVisible();
        expect(screen.getByText(/suburb-level only — no street address, no pin/i)).toBeVisible();
    });
    it('shows available unit listings inside the selected complex, without internal unit identifiers', async () => {
        mocks.get.mockResolvedValue(detail({
            available_units: [{
                title: 'Two-bedroom garden residence',
                description: 'A light-filled home with a private garden.',
                bedrooms: 2,
                bathrooms: 1,
                size_m2: '88.00',
                amenities: ['Private garden', 'Secure parking'],
                availability_status: 'available',
                photos: [{ public_id: 'unit-photo-1', caption: 'Garden-facing lounge' }],
            }],
        }));
        renderPage();
        expect(await screen.findByRole('heading', { name: 'Two-bedroom garden residence' })).toBeVisible();
        expect(screen.getByText(/2 bedrooms.*1 bathrooms.*88 m²/i)).toBeVisible();
        expect(screen.getByText('Private garden')).toBeVisible();
        expect(screen.getByAltText('Garden-facing lounge')).toHaveAttribute('src', 'http://api.test/photo/unit-photo-1?size=thumb');
        expect(screen.queryByText('A-101')).not.toBeInTheDocument();
    });
    it('reserves the gallery box while the estate loads', async () => {
        mocks.get.mockReturnValue(new Promise(() => { }));
        const { container } = renderPage();
        const status = await screen.findByRole('status');
        expect(status).toHaveTextContent(/loading this complex/i);
        expect(status.closest('[aria-busy="true"]')).not.toBeNull();
        expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
    });
    it('tells a private estate apart from a failed request', async () => {
        mocks.get.mockRejectedValue(new ApiError(404, 'Not found.', 'NOT_FOUND', 'req-404'));
        renderPage();
        expect(await screen.findByText(/that complex is not published/i)).toBeVisible();
        expect(screen.getByRole('link', { name: /back to the directory/i })).toBeVisible();
    });
    it('carries the selected complex into either access path without treating it as membership', async () => {
        mocks.get.mockResolvedValue(detail());
        const user = userEvent.setup();
        renderPage();
        await screen.findByRole('heading', { level: 1, name: 'Ridge Close' });
        const requestAccess = screen.getByRole('link', { name: 'Request access' });
        expect(requestAccess).toHaveAttribute('href', '/register');
        await user.click(requestAccess);
        expect(screen.getByText('Resident account route')).toBeVisible();
        expect(JSON.parse(window.sessionStorage.getItem('valora.public-estate-selection'))).toMatchObject({
            estate_id: 1,
            name: 'Ridge Close',
        });
    });
});
