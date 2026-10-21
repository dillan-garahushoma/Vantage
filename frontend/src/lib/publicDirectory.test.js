/**
 * The public directory's two pure helpers.
 *
 * The photo URL is built from the opaque `public_id` the API returns — never from
 * an estate id or a filename — and the alt text always exists, because a
 * published profile is read by people who cannot see the photograph.
 */
import { describe, expect, it } from 'vitest';
import { PUBLIC_PAGE_SIZE, photoAlt, publicPhotoUrl } from './publicDirectory';
describe('publicPhotoUrl', () => {
    it('addresses one stored photo by its public id, with the requested size', () => {
        expect(publicPhotoUrl('abc123', 'thumb')).toMatch(/\/api\/v1\/public\/photos\/abc123\?size=thumb$/);
        expect(publicPhotoUrl('abc123')).toMatch(/\/api\/v1\/public\/photos\/abc123\?size=full$/);
    });
    it('escapes an id rather than letting it change the path', () => {
        expect(publicPhotoUrl('a/b c')).toContain(encodeURIComponent('a/b c'));
    });
    it('keeps the page size within the API maximum of 50', () => {
        expect(PUBLIC_PAGE_SIZE).toBeLessThanOrEqual(50);
        expect(PUBLIC_PAGE_SIZE).toBeGreaterThan(0);
    });
});
describe('photoAlt', () => {
    it('uses the caption when there is one', () => {
        expect(photoAlt('Ridge Close', 'The pool at dusk')).toBe('The pool at dusk');
        expect(photoAlt('Ridge Close', '  spaced  ')).toBe('spaced');
    });
    it('falls back to the estate name instead of leaving an image unlabelled', () => {
        expect(photoAlt('Ridge Close', null)).toBe('Photo of Ridge Close');
        expect(photoAlt('Ridge Close', undefined)).toBe('Photo of Ridge Close');
        expect(photoAlt('Ridge Close', '   ')).toBe('Photo of Ridge Close');
    });
});
