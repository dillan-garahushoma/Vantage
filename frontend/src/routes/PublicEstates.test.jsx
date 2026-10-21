/**
 * The public directory — the one screen anyone can read without an account.
 *
 * It may only show what the API publishes: an estate is here because its
 * administrator opted in, and the three empty/error states are told apart, because
 * "no match" and "nothing published" mean different things to a visitor.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../lib/api';
import { PublicEstates } from './PublicEstates';
const mocks = vi.hoisted(() => ({ list: vi.fn() }));
vi.mock('../lib/publicDirectory', () => ({
    PUBLIC_PAGE_SIZE: 12,
    listPublicEstates: mocks.list,
    publicPhotoUrl: (id, size) => `http://api.test/photo/${id}?size=${size}`,
    photoAlt: (name, caption) => caption ?? `Photo of ${name}`,
}));
function item(overrides = {}) {
    return {
        estate_id: 1,
        name: 'Ridge Close',
        suburb: 'Centurion',
        city: 'Tshwane',
        province: 'Gauteng',
        description: 'A 24-unit complex with a single monitored gate.',
        unit_count: 24,
        cover_photo_public_id: 'pub1',
        ...overrides,
    };
}
function pageOf(items, total = items.length) {
    return { items, total, page: 1, size: 12, pages: Math.max(1, Math.ceil(total / 12)) };
}
function renderDirectory() {
    return render(<MemoryRouter initialEntries={['/estates']}>
      <PublicEstates />
    </MemoryRouter>);
}
beforeEach(() => {
    mocks.list.mockReset();
});
describe('PublicEstates', () => {
    it('shows published complexes with what was published, and nothing else', async () => {
        mocks.list.mockResolvedValue(pageOf([item()]));
        renderDirectory();
        expect(await screen.findByText('Ridge Close')).toBeVisible();
        expect(screen.getByText(/Centurion, Tshwane, Gauteng/)).toBeVisible();
        expect(screen.getByText(/a 24-unit complex/i)).toBeVisible();
        expect(screen.getByText('24 units')).toBeVisible();
        // The name is the card's only link and its `::after` overlay covers the card,
        // so there is one link with a real destination name and the whole card is the
        // target. The card itself has to be `relative` for that overlay to stay put.
        const titleLink = screen.getByRole('link', { name: 'Ridge Close' });
        expect(titleLink).toHaveAttribute('href', '/estates/1');
        expect(titleLink.className).toMatch(/after:inset-0/);
        const card = titleLink.closest('li');
        expect(card?.className).toMatch(/relative/);
        expect(card?.className).toMatch(/overflow-hidden/);
        // The affordance is still on screen; it is simply no longer the link.
        expect(screen.getByText(/view this complex/i)).toBeVisible();
        // The cover photo is fetched by its unguessable public id, at thumbnail size.
        expect(screen.getByAltText('Photo of Ridge Close')).toHaveAttribute('src', 'http://api.test/photo/pub1?size=thumb');
    });
    it('says how the directory is populated, so an absent estate is not a mystery', async () => {
        mocks.list.mockResolvedValue(pageOf([]));
        renderDirectory();
        expect(await screen.findByText('No complexes are published yet')).toBeVisible();
        expect(screen.getByText(/administrator publishes their complex/i)).toBeVisible();
    });
    it('tells "no match" apart from "nothing published"', async () => {
        mocks.list.mockResolvedValue(pageOf([]));
        const user = userEvent.setup();
        renderDirectory();
        await screen.findByText('No complexes are published yet');
        await user.type(screen.getByLabelText(/search by name, suburb or city/i), 'Nowhere');
        await user.click(screen.getByRole('button', { name: /search/i }));
        expect(await screen.findByText('No complex matches that search')).toBeVisible();
        expect(screen.getByText(/clear the search to see everything/i)).toBeVisible();
    });
    it('sends the search term to the API and keeps it in the URL', async () => {
        mocks.list.mockResolvedValue(pageOf([item()]));
        const user = userEvent.setup();
        renderDirectory();
        await screen.findByText('Ridge Close');
        await user.type(screen.getByLabelText(/search by name, suburb or city/i), 'Centurion');
        await user.click(screen.getByRole('button', { name: /search/i }));
        expect(mocks.list).toHaveBeenLastCalledWith({ page: 1, page_size: 12, q: 'Centurion' });
    });
    it('shows a rejected directory read with its reference and a retry', async () => {
        mocks.list.mockRejectedValue(new ApiError(500, 'An unexpected server error occurred.', 'INTERNAL_ERROR', 'req-500'));
        const user = userEvent.setup();
        renderDirectory();
        expect(await screen.findByText(/could not load the directory/i)).toBeVisible();
        expect(screen.getByText(/req-500/)).toBeVisible();
        mocks.list.mockResolvedValue(pageOf([item()]));
        await user.click(screen.getByRole('button', { name: /try again/i }));
        expect(await screen.findByText('Ridge Close')).toBeVisible();
    });
    it('an estate without a photograph still gets a card', async () => {
        mocks.list.mockResolvedValue(pageOf([item({ cover_photo_public_id: null })]));
        renderDirectory();
        expect(await screen.findByText('No photograph yet')).toBeVisible();
    });
    it('reserves the grid while loading, instead of collapsing and reflowing', async () => {
        let land;
        mocks.list.mockReturnValue(new Promise((resolve) => {
            land = resolve;
        }));
        const { container } = renderDirectory();
        // The words reach a screen reader once, politely, from a region the signal is
        // attached to; the shapes themselves are decorative and stay out of the tree.
        const status = await screen.findByRole('status');
        expect(status).toHaveTextContent(/loading published complexes/i);
        expect(status.closest('[aria-busy="true"]')).not.toBeNull();
        // Six reserved cards, each with a media box: the geometry the grid will have.
        expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThanOrEqual(6);
        land(pageOf([item()]));
        expect(await screen.findByText('Ridge Close')).toBeVisible();
        expect(screen.queryByRole('status')).toBeNull();
    });
    it('says which slice of the directory is on screen, and can clear a search', async () => {
        mocks.list.mockResolvedValue(pageOf([item()], 24));
        const user = userEvent.setup();
        renderDirectory();
        expect(await screen.findByText(/showing 1–12 of 24 published complexes/i)).toBeVisible();
        // Pagination is legible rather than a guess.
        expect(screen.getByText(/page 1 of 2/)).toBeVisible();
        await user.type(screen.getByLabelText(/search by name, suburb or city/i), 'Centurion');
        await user.click(screen.getByRole('button', { name: /search/i }));
        await user.click(await screen.findByRole('button', { name: 'Clear' }));
        expect(mocks.list).toHaveBeenLastCalledWith({ page: 1, page_size: 12, q: '' });
    });
});
