/**
 * Residency approvals: the resident's request and the administrator's queue.
 *
 * Same conventions as the rest of the API surface:
 *
 * * `estate_id` is a **scope selector** on every admin call, never proof of
 *   access; the server re-resolves the caller's `hoa_admin` membership and answers
 *   the 403/404 from that.
 * * The decision is the endpoint (`approve` / `reject`), not a status field. There
 *   is deliberately no "set status" call a client could use to self-approve.
 * * Submitting carries an estate id in the body because the resident is *asking*
 *   to join — it cannot be proof of access, and the server still verifies the
 *   estate and the unit exist.
 * * No maths and no client-side permission logic: the pending count is the
 *   server's number.
 */
import { api } from './api';
/** Ask to be admitted to one unit of one estate. Never grants access itself. */
export function submitResidencyRequest(body) {
    return api.post('/api/v1/residency-requests', body);
}
/** The caller's own requests, newest first, across every estate. */
export function listMyResidencyRequests() {
    return api.get('/api/v1/residency-requests/mine');
}
/* ------------------------------------------------------------ admin queue */
export function listResidencyRequests(estateId, params = {}) {
    return api.get('/api/v1/residency-requests', {
        estate_id: estateId,
        status: params.status || undefined,
        search: params.search?.trim() || undefined,
        page: params.page ?? 1,
        page_size: params.page_size ?? 20,
    });
}
export function pendingResidencyCount(estateId) {
    return api.get('/api/v1/residency-requests/pending-count', {
        estate_id: estateId,
    });
}
export function approveResidencyRequest(estateId, requestId) {
    return api.post(`/api/v1/residency-requests/${requestId}/approve`, undefined, { estate_id: estateId });
}
export function rejectResidencyRequest(estateId, requestId, note) {
    return api.post(`/api/v1/residency-requests/${requestId}/reject`, { note: note?.trim() || null }, { estate_id: estateId });
}
/** The plain-language label and tone for a status. Colour is never the only cue. */
export const RESIDENCY_STATUS = {
    pending: {
        label: 'Awaiting review',
        hint: 'An estate administrator still has to approve this request.',
        tone: 'warn',
    },
    approved: {
        label: 'Approved',
        hint: 'You are a resident of this unit and can use the estate’s screens.',
        tone: 'good',
    },
    rejected: {
        label: 'Not approved',
        hint: 'The estate office declined this request. Contact them if that is unexpected.',
        tone: 'alert',
    },
};
/** Narrow an arbitrary string from the API into the known status vocabulary. */
export function asResidencyStatus(value) {
    return value === 'approved' || value === 'rejected' ? value : 'pending';
}
