/**
 * The public directory: the only calls in the app that work without an account.
 *
 * These endpoints are unauthenticated by design, so nothing here sends a token
 * expectation: the server decides what may be published (an estate must set
 * `is_public`, and a score only appears when it also set `show_living_score`).
 * The client never filters for privacy — it cannot unintentionally widen what the
 * API returns, because the API returns the allow-listed DTOs and nothing else.
 */
import { api, API_BASE } from './api';
export const PUBLIC_PAGE_SIZE = 12;
export function listPublicEstates(params) {
    return api.get('/api/v1/public/estates', {
        page: params.page ?? 1,
        page_size: params.page_size ?? PUBLIC_PAGE_SIZE,
        q: params.q?.trim() || undefined,
    });
}
export function getPublicEstate(estateId) {
    return api.get(`/api/v1/public/estates/${estateId}`);
}
/**
 * The URL of one stored photo. Images are served under the unguessable
 * `public_id`, and the size is one of the two the API produces.
 */
export function publicPhotoUrl(publicId, size = 'full') {
    return `${API_BASE}/api/v1/public/photos/${encodeURIComponent(publicId)}?size=${size}`;
}
/** Alt text for a photo: its caption, or a plain description of the image. */
export function photoAlt(estateName, caption) {
    const trimmed = caption?.trim();
    return trimmed ? trimmed : `Photo of ${estateName}`;
}
