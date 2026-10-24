/**
 * The estate's photograph mosaic.
 *
 * Two things are worth pinning. The **arithmetic**, because an off-by-one in the
 * overflow count either hides photograph number six from everybody or promises
 * "+2 more" over a gallery that has already shown them all. And the **tile**,
 * because "more photographs than fit" is the case a gallery is most likely to
 * get quietly wrong: an estate with twenty photographs that silently ends at
 * five reads as an estate with five.
 */
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PhotoGallery, mosaic } from './PhotoGallery';
vi.mock('../lib/publicDirectory', () => ({
    publicPhotoUrl: (id, size) => `http://api.test/photo/${id}?size=${size}`,
    photoAlt: (name, caption) => caption ?? `Photo of ${name}`,
}));
function photos(count) {
    return Array.from({ length: count }, (_, index) => ({
        public_id: `p${index + 1}`,
        caption: index === 0 ? 'The pool at dusk' : null,
    }));
}
function renderGallery(count) {
    return render(<PhotoGallery estateName="Ridge Close" photos={photos(count)}/>);
}
beforeEach(() => {
    vi.clearAllMocks();
});
describe('mosaic — the tile arithmetic', () => {
    it('never hides or over-counts a photograph, for every size from one to twenty', () => {
        for (let count = 1; count <= 20; count += 1) {
            const { tiles, clear, overflow } = mosaic(count);
            // What is shown clearly plus what the last tile conceals is everything.
            expect(clear + overflow, `count=${count}`).toBe(count);
            // Never more tiles than the arrangement has slots.
            expect(clear + (overflow > 0 ? 1 : 0), `count=${count}`).toBeLessThanOrEqual(tiles.length);
            // The overflow count is always a real remainder.
            if (overflow > 0)
                expect(overflow, `count=${count}`).toBeGreaterThan(1);
        }
    });
    it('shows everything and blurs nothing while the photographs fit', () => {
        for (let count = 1; count <= 5; count += 1) {
            const { clear, overflow } = mosaic(count);
            expect(clear, `count=${count}`).toBe(count);
            expect(overflow, `count=${count}`).toBe(0);
        }
    });
    it('uses a complete two-by-two collage when four photographs are published', () => {
        renderGallery(4);
        for (let index = 1; index <= 4; index += 1) {
            expect(screen.getByRole('button', {
                name: new RegExp(`open photograph ${index} of 4`, 'i'),
            })).toBeVisible();
        }
        expect(screen.getByRole('button', { name: /open photograph 1 of 4/i }).parentElement)
            .toHaveClass('grid', 'w-full', 'grid-cols-2');
    });
    it('keeps the 1 + 4 arrangement and conceals the rest', () => {
        // Five slots, so four stay clear and the fifth tile carries what is left.
        expect(mosaic(6)).toMatchObject({ clear: 4, overflow: 2 });
        expect(mosaic(20)).toMatchObject({ clear: 4, overflow: 16 });
        expect(mosaic(5)).toMatchObject({ clear: 5, overflow: 0 });
        expect(mosaic(4)).toMatchObject({ clear: 4, overflow: 0 });
    });
    it('uses a large lead image with balanced supporting tiles', () => {
        expect(mosaic(3).grid).toContain('lg:grid-cols-2');
        expect(mosaic(3).tiles[0]).toContain('lg:row-span-2');
        expect(mosaic(4).grid).toContain('lg:grid-cols-4');
        expect(mosaic(4).tiles[0]).toContain('lg:col-span-2');
        expect(mosaic(4).tiles[0]).toContain('lg:row-span-2');
        expect(mosaic(5).tiles[0]).toContain('lg:col-span-2');
        expect(mosaic(5).tiles[0]).toContain('lg:row-span-2');
    });
});
describe('PhotoGallery — more photographs than the mosaic can show', () => {
    it('reserves a consistent desktop height for the photo collage', () => {
        renderGallery(5);
        const lead = screen.getByRole('button', { name: /open photograph 1 of 5/i });
        expect(lead.parentElement?.parentElement?.className).toContain('lg:h-[320px]');
        expect(lead.parentElement?.parentElement?.className).toContain('xl:h-[380px]');
    });
    it('counts the concealed photographs on the last tile instead of ending at five', () => {
        renderGallery(12);
        // 4 clear + 8 concealed = the 12 that were published.
        expect(screen.getByText('+8 more')).toBeVisible();
        expect(screen.getByRole('button', { name: /show all 12 photographs, including 8 not shown/i })).toBeVisible();
        expect(screen.getByRole('button', { name: /open photograph 4 of 12/i })).toBeVisible();
        // The fifth clear tile does not exist: the overflow tile took its slot.
        expect(screen.queryByRole('button', { name: /open photograph 5 of 12/i })).toBeNull();
    });
    it('blurs and counts nothing when every photograph already fits', () => {
        renderGallery(5);
        expect(screen.queryByText(/\+.*more/)).toBeNull();
        for (let index = 1; index <= 5; index += 1) {
            expect(screen.getByRole('button', { name: new RegExp(`open photograph ${index} of 5`, 'i') }))
                .toBeVisible();
        }
        expect(screen.queryByRole('button', { name: /not shown here/i })).toBeNull();
    });
    it('opens the full gallery on the first photograph the tile conceals', async () => {
        const user = userEvent.setup();
        renderGallery(12);
        await user.click(screen.getByRole('button', { name: /show all 12 photographs, including 8 not shown/i }));
        const viewer = await screen.findByRole('dialog');
        // The tile stands for photographs 5 to 12, so it opens at the fifth — not
        // back at the first, which the visitor has already seen.
        expect(within(viewer).getByText('5 of 12')).toBeVisible();
        // And the whole gallery is there to step through, not just the mosaic.
        expect(within(viewer).getByRole('button', { name: /next photograph/i })).toBeVisible();
    });
    it('still offers the plain button where the mosaic tiles are hidden', () => {
        renderGallery(12);
        // Below `lg` the tiles past the first are hidden, so the button is the only
        // way in and must stay; the overflow tile hides itself instead.
        expect(screen.getByRole('button', { name: /show all 12 photos/i })).toBeVisible();
        expect(screen.getByText('+8 more').closest('button')?.className).toContain('hidden lg:block');
    });
    it('says nothing at all when the estate published no photographs', () => {
        render(<PhotoGallery estateName="Ridge Close" photos={[]}/>);
        expect(screen.getByText('No photographs published yet')).toBeVisible();
        expect(screen.queryByText(/more/)).toBeNull();
    });
});
