import { api, ApiError } from './api';
const BRIEF_PATH = '/api/v1/analytics/health-brief';
/** The stored brief, or the deterministic template when no AI brief exists. */
export function readHealthBrief(estateId) {
    return api.get(BRIEF_PATH, { estate_id: estateId });
}
/**
 * Ask for the AI brief (HOA admin only). Idempotent, and a provider failure is
 * answered as a template brief with `ai_unavailable_reason` set — not an error.
 */
export function generateHealthBrief(estateId) {
    return api.post(BRIEF_PATH, undefined, { estate_id: estateId });
}
export function sendHealthBriefFeedback(estateId, insightId, payload) {
    return api.post(`${BRIEF_PATH}/${insightId}/feedback`, payload, {
        estate_id: estateId,
    });
}
const suggestionPath = (complaintId) => `/api/v1/complaints/${complaintId}/ai-suggestion`;
/** The stored suggestion, or 404 when none has been requested. */
export function readTriageSuggestion(estateId, complaintId) {
    return api.get(suggestionPath(complaintId), { estate_id: estateId });
}
/** Ask for the suggestion (HOA admin only). Idempotent: one suggestion per complaint. */
export function requestTriageSuggestion(estateId, complaintId) {
    return api.post(suggestionPath(complaintId), undefined, {
        estate_id: estateId,
    });
}
/** Accept, override or dismiss — once, and never both. */
export function decideTriageSuggestion(estateId, complaintId, payload) {
    return api.post(`${suggestionPath(complaintId)}/decision`, payload, {
        estate_id: estateId,
    });
}
/**
 * The AI layer being off, out of budget or failing is a normal state, not an
 * incident: the panel says so quietly and the product keeps working.
 */
export function isAiUnavailable(error) {
    return error.status === 503 && error.code === 'AI_UNAVAILABLE';
}
