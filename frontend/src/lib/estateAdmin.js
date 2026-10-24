/**
 * The estate administrator's and provider's API surface.
 *
 * Conventions this file follows:
 *
 * * **`estate_id` is a scope selector, never proof of access.** It is passed as a
 *   query parameter because that is the contract; the server re-resolves the
 *   caller's membership on every call and answers 403/404 from that.
 * * **The server is the authority on limits.** The uploader knows the accepted
 *   types and the 5 MB hint so it can say something useful before spending a
 *   user's bandwidth, but a rejection always comes back as the server's own
 *   message, shown unchanged.
 * * **No maths.** Nothing here computes a score, a percentage, an average or a
 *   total; it calls the API and hands back what came out.
 */
import { ApiError, api, API_BASE, session } from './api';
/* ------------------------------------------------------------------ profile */
export function getEstateProfile(estateId) {
    return api.get('/api/v1/estates/profile', { estate_id: estateId });
}
export function updateEstateProfile(estateId, changes) {
    return api.patch('/api/v1/estates/profile', changes, { estate_id: estateId });
}
/* ------------------------------------------------------------------- photos */
export function listEstatePhotos(estateId) {
    return api.get('/api/v1/estates/photos', { estate_id: estateId });
}
export function updateEstatePhoto(estateId, photoId, changes) {
    return api.patch(`/api/v1/estates/photos/${photoId}`, changes, {
        estate_id: estateId,
    });
}
export function deleteEstatePhoto(estateId, photoId) {
    return api.remove(`/api/v1/estates/photos/${photoId}`, { estate_id: estateId });
}
/** What the picker hints at before a byte is spent. The server still decides. */
export const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
export const MAX_UPLOAD_BYTES = 5 * 1024 * 1024;
/**
 * Mirrors `MAX_PHOTOS_PER_ESTATE` in the photo service. The server enforces it
 * and answers 409 when it is reached; the picker counts against it so a batch
 * is never queued only for the last one to be refused.
 */
export const MAX_ESTATE_PHOTOS = 12;
export const UPLOAD_HINT = `JPEG, PNG or WebP · up to ${MAX_UPLOAD_BYTES / (1024 * 1024)} MB each · up to ${MAX_ESTATE_PHOTOS} photos per estate`;
/** "JPEG, PNG or WEBP" — the accepted types as a person reads them. */
export const ACCEPTED_IMAGE_LABEL = ACCEPTED_IMAGE_TYPES.map((type) => type.replace('image/', '').toUpperCase()).join(', ');
export function uploadEstatePhoto(estateId, file, options = {}) {
    // XMLHttpRequest rather than fetch: it is the only way to report bytes sent,
    // and this is the one place where a real progress bar matters.
    return new Promise((resolve, reject) => {
        const form = new FormData();
        form.append('file', file);
        if (options.caption)
            form.append('caption', options.caption.slice(0, 140));
        const request_ = new XMLHttpRequest();
        request_.open('POST', `${API_BASE}/api/v1/estates/photos?estate_id=${estateId}`);
        request_.setRequestHeader('Accept', 'application/json');
        const token = session.token();
        if (token)
            request_.setRequestHeader('Authorization', `Bearer ${token}`);
        request_.upload.onprogress = (event) => {
            if (event.lengthComputable && options.onProgress) {
                options.onProgress(Math.round((event.loaded / event.total) * 100));
            }
        };
        request_.onload = () => {
            let payload = null;
            try {
                payload = request_.responseText ? JSON.parse(request_.responseText) : null;
            }
            catch {
                payload = null;
            }
            if (request_.status >= 200 && request_.status < 300) {
                resolve(payload);
                return;
            }
            const detail = payload?.detail;
            const shaped = detail && typeof detail === 'object'
                ? detail
                : undefined;
            reject(new ApiError(request_.status, shaped?.message ??
                (typeof detail === 'string' ? detail : 'The photo was rejected.'), shaped?.code, shaped?.request_id));
        };
        request_.onerror = () => reject(new ApiError(0, 'Cannot reach the VALORA API. Is the backend running?'));
        request_.send(form);
    });
}
/* ---------------------------------------------------------------- members */
export function listEstateMembers(estateId, params = {}) {
    return api.get('/api/v1/memberships', {
        estate_id: estateId,
        role: params.role || undefined,
        page: params.page ?? 1,
        page_size: params.page_size ?? 20,
    });
}
export function removeEstateMember(estateId, membershipId) {
    return api.remove(`/api/v1/memberships/${membershipId}`, { estate_id: estateId });
}
export function transferEstateMemberUnit(estateId, membershipId, propertyId) {
    return api.patch(`/api/v1/memberships/${membershipId}/unit`, { property_id: propertyId }, {
        estate_id: estateId,
    });
}
export function listEstateProperties(estateId) {
    return api.get('/api/v1/properties', { estate_id: estateId, page: 1, size: 100 });
}
export function listProviderApplications(estateId, status) {
    return api.get('/api/v1/provider-applications', { estate_id: estateId, status });
}
export function approveProviderApplication(estateId, applicationId) {
    return api.post(`/api/v1/provider-applications/${applicationId}/approve`, {}, {
        estate_id: estateId,
    });
}
export function rejectProviderApplication(estateId, applicationId) {
    return api.post(`/api/v1/provider-applications/${applicationId}/reject`, {}, {
        estate_id: estateId,
    });
}
/* -------------------------------------------------------------- join codes */
export function currentJoinCode(estateId) {
    return api.get('/api/v1/join-codes/current', { estate_id: estateId });
}
export function rotateJoinCode(estateId, expiresInDays) {
    return api.post('/api/v1/join-codes', { expires_in_days: expiresInDays ?? null }, {
        estate_id: estateId,
    });
}
/** Redeem a code for a unit. The estate comes from the code, never the body. */
export function joinEstateWithCode(code, unitNo) {
    return api.post('/api/v1/memberships/join', {
        code: code.trim(),
        unit_no: unitNo.trim(),
    });
}
export function createUnitsBulk(estateId, units) {
    return api.post('/api/v1/properties/bulk', { units }, { estate_id: estateId });
}
/* -------------------------------------------------------------- providers */
export function listEstateProviders(estateId, params = {}) {
    return api.get('/api/v1/providers', {
        estate_id: estateId,
        page: params.page ?? 1,
        size: params.size ?? 20,
        trade: params.trade || undefined,
    });
}
export function getMyProviderProfile() {
    return api.get('/api/v1/providers/me');
}
/* ------------------------------------------------------------ work orders */
export function listMyWorkOrders(estateId, params = {}) {
    return api.get('/api/v1/work-orders/mine', {
        estate_id: estateId,
        page: params.page ?? 1,
        size: params.size ?? 20,
    });
}
export function listEstateWorkOrders(estateId, params = {}) {
    return api.get('/api/v1/work-orders', {
        estate_id: estateId,
        page: params.page ?? 1,
        size: params.size ?? 20,
    });
}
/**
 * Assign a provider to a complaint. A work order is always the assignment of a
 * provider to a complaint — there is no free-standing job record to create.
 */
export function createWorkOrder(estateId, body) {
    return api.post('/api/v1/work-orders', body, { estate_id: estateId });
}
export function updateWorkOrder(estateId, workOrderId, changes) {
    return api.patch(`/api/v1/work-orders/${workOrderId}`, changes, {
        estate_id: estateId,
    });
}
export function rateWorkOrder(estateId, workOrderId, rating) {
    return api.post(`/api/v1/work-orders/${workOrderId}/rating`, { rating }, { estate_id: estateId });
}
/** The work order raised for one complaint: its author, or an estate admin. */
export function getComplaintWorkOrder(estateId, complaintId) {
    return api.get(`/api/v1/complaints/${complaintId}/work-order`, {
        estate_id: estateId,
    });
}
/** Reopening preserves the original repair record; the server starts a new review cycle. */
export function reopenComplaint(estateId, complaintId, note) {
    return api.post(`/api/v1/complaints/${complaintId}/reopen`, { note }, {
        estate_id: estateId,
    });
}
/** "unit_no, street address, size, bedrooms, bathrooms" per line. */
export function parseUnitLines(text) {
    const lines = [];
    const rejected = [];
    text
        .split(/\r?\n/)
        .forEach((raw, index) => {
        const line = raw.trim();
        if (!line)
            return;
        const [unitNo, street, size, bedrooms, bathrooms] = line
            .split(',')
            .map((part) => part.trim());
        if (!unitNo) {
            rejected.push(index + 1);
            return;
        }
        const entry = { unit_no: unitNo };
        if (street)
            entry.street_address = street;
        if (size)
            entry.size_m2 = Number(size);
        if (bedrooms)
            entry.bedrooms = Number(bedrooms);
        if (bathrooms)
            entry.bathrooms = Number(bathrooms);
        if ((entry.size_m2 !== undefined && Number.isNaN(entry.size_m2)) ||
            (entry.bedrooms !== undefined && Number.isNaN(entry.bedrooms)) ||
            (entry.bathrooms !== undefined && Number.isNaN(entry.bathrooms))) {
            rejected.push(index + 1);
            return;
        }
        lines.push(entry);
    });
    return { lines, rejected };
}
