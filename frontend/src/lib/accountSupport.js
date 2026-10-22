import { api } from './api';

/** Account support calls are deliberately separate from estate administration. */
export function listNotifications(estateId, params = {}) {
    return api.get('/api/v1/notifications', {
        estate_id: estateId,
        page: params.page ?? 1,
        size: params.size ?? 50,
    });
}
export function markNotificationRead(estateId, notificationId) {
    return api.post(`/api/v1/notifications/${notificationId}/read`, undefined, {
        estate_id: estateId,
    });
}
export function getNotificationPreferences() {
    return api.get('/api/v1/auth/preferences');
}
export function updateNotificationPreferences(preferences) {
    return api.patch('/api/v1/auth/preferences', preferences);
}
export function requestPasswordRecovery(email) {
    return api.post('/api/v1/auth/recovery/request', { email });
}
export function confirmPasswordRecovery(token, password) {
    return api.post('/api/v1/auth/recovery/confirm', { token, password });
}
